"""JSON / ZIP 备份 + 恢复业务。

JSON 导出：序列化所有业务表到 dict（附件只存元数据）。
ZIP 导出：JSON + attachments/ 目录打包，单文件恢复。

恢复：单事务覆盖（清空后按依赖顺序插入），FK 期间关闭。
"""
import io
import json
import zipfile
from copy import deepcopy
from datetime import date, datetime
from pathlib import Path

from sqlalchemy import Date, DateTime, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.database import DATA_DIR
from app.models import (
    Attachment, Cost, CostCategory, InboxItem, Project, Task, TaskDependency,
)


EXPORT_VERSION = 3
SUPPORTED_VERSIONS = (1, 2, 3)
REQUIRED_TABLES_V12 = (
    "projects", "tasks", "task_dependencies", "costs",
    "cost_categories", "inbox_items",
)
REQUIRED_TABLES_V3 = REQUIRED_TABLES_V12 + ("attachments",)


def _row_to_dict(row) -> dict:
    result = {}
    for col in row.__table__.columns:
        val = getattr(row, col.name)
        if hasattr(val, "isoformat"):
            val = val.isoformat()
        result[col.name] = val
    return result


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------


def export_data(db: Session) -> dict:
    return {
        "version": EXPORT_VERSION,
        "exported_at": datetime.utcnow().isoformat() + "Z",
        "projects": [_row_to_dict(p) for p in db.query(Project).order_by(Project.id).all()],
        "tasks": [_row_to_dict(t) for t in db.query(Task).order_by(Task.id).all()],
        "task_dependencies": [_row_to_dict(d) for d in db.query(TaskDependency).order_by(TaskDependency.id).all()],
        "costs": [_row_to_dict(c) for c in db.query(Cost).order_by(Cost.id).all()],
        "cost_categories": [_row_to_dict(c) for c in db.query(CostCategory).order_by(CostCategory.id).all()],
        "inbox_items": [_row_to_dict(i) for i in db.query(InboxItem).order_by(InboxItem.id).all()],
        "attachments": [_row_to_dict(a) for a in db.query(Attachment).order_by(Attachment.id).all()],
    }


def export_full(db: Session) -> tuple[bytes, str]:
    """Return (zip_bytes, filename) with JSON + attachment files bundled."""
    payload = export_data(db)

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("backup.json", json.dumps(payload, ensure_ascii=False, indent=2))
        base = DATA_DIR / "attachments"
        if base.exists():
            for path in base.rglob("*"):
                if path.is_file():
                    arcname = f"attachments/{path.relative_to(base).as_posix()}"
                    zf.write(path, arcname)

    filename = f"pm-backup-full-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}.zip"
    return buf.getvalue(), filename


# ---------------------------------------------------------------------------
# Validation / normalization
# ---------------------------------------------------------------------------


def _validate_payload(payload: dict) -> None:
    if not isinstance(payload, dict):
        raise ValueError("备份文件不是有效的 JSON 对象")
    version = payload.get("version")
    if type(version) is not int or version not in SUPPORTED_VERSIONS:
        raise ValueError(f"备份版本不支持（支持 1、2、3，得到 {version}）")
    required = REQUIRED_TABLES_V3 if version >= 3 else REQUIRED_TABLES_V12
    missing = [key for key in required if key not in payload]
    if missing:
        raise ValueError(f"备份缺少数据表: {', '.join(missing)}")
    for key in required:
        rows = payload[key]
        if not isinstance(rows, list):
            raise ValueError(f"备份表 {key} 必须是数组")
        if any(not isinstance(row, dict) for row in rows):
            raise ValueError(f"备份表 {key} 包含无效记录")


def _normalize_payload(payload: dict) -> dict:
    normalized = deepcopy(payload)
    _validate_payload(normalized)

    for index, cost in enumerate(normalized["costs"]):
        if normalized["version"] == 1:
            candidates = (cost.get("description"), cost.get("category"))
            name = next(
                (
                    candidate.strip()
                    for candidate in candidates
                    if isinstance(candidate, str) and candidate.strip()
                ),
                None,
            )
            if name is None:
                raise ValueError(
                    f"备份表 costs 第 {index + 1} 条记录无法生成名称"
                )
            cost["name"] = name[:200]
            continue

        name = cost.get("name")
        if not isinstance(name, str):
            raise ValueError(f"备份表 costs 第 {index + 1} 条记录名称必须是字符串")
        name = name.strip()
        if not name:
            raise ValueError(f"备份表 costs 第 {index + 1} 条记录名称不能为空")
        if len(name) > 200:
            raise ValueError(f"备份表 costs 第 {index + 1} 条记录名称不能超过 200 个字符")
        cost["name"] = name

    return normalized


def _prepare_rows(payload: dict) -> dict[str, list[object]]:
    model_by_key = {
        "projects": Project,
        "cost_categories": CostCategory,
        "tasks": Task,
        "task_dependencies": TaskDependency,
        "costs": Cost,
        "inbox_items": InboxItem,
    }
    if payload["version"] >= 3:
        model_by_key["attachments"] = Attachment

    prepared = {}
    for key, model in model_by_key.items():
        columns = {c.name for c in model.__table__.columns}
        for index, row in enumerate(payload[key]):
            missing = columns - row.keys()
            if missing:
                raise ValueError(
                    f"备份表 {key} 第 {index + 1} 条记录缺少字段: {', '.join(sorted(missing))}"
                )
        prepared[key] = [_dict_to_row(model, row) for row in payload[key]]
    return prepared


# ---------------------------------------------------------------------------
# Restore
# ---------------------------------------------------------------------------


def restore_data(db: Session, payload: dict) -> dict[str, int]:
    """Restore JSON-only backup.  Attachment files (if any in payload) are ignored
    unless restore_full is used.
    """
    counts = _restore_internal(db, payload, attachment_files=None)
    return counts


def restore_full(db: Session, zip_bytes: bytes) -> dict[str, int]:
    """Restore from a ZIP bundle.  Extracts backup.json + attachments/."""
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        try:
            json_bytes = zf.read("backup.json")
        except KeyError:
            raise ValueError("备份 zip 缺少 backup.json")
        payload = json.loads(json_bytes.decode("utf-8"))

        attachment_files: dict[str, bytes] = {}
        for name in zf.namelist():
            if name.startswith("attachments/") and not name.endswith("/"):
                attachment_files[name.removeprefix("attachments/")] = zf.read(name)

    counts = _restore_internal(db, payload, attachment_files=attachment_files)
    return counts


def _restore_internal(
    db: Session,
    payload: dict,
    attachment_files: dict[str, bytes] | None,
) -> dict[str, int]:
    normalized = _normalize_payload(payload)
    prepared = _prepare_rows(normalized)

    db.execute(text("PRAGMA foreign_keys = OFF"))
    try:
        db.query(Attachment).delete()
        db.query(InboxItem).delete()
        db.query(TaskDependency).delete()
        db.query(Cost).delete()
        db.query(Task).delete()
        db.query(Project).delete()
        db.query(CostCategory).delete()

        counts = {}
        for model, key in [
            (Project, "projects"),
            (CostCategory, "cost_categories"),
            (Task, "tasks"),
            (TaskDependency, "task_dependencies"),
            (Cost, "costs"),
            (InboxItem, "inbox_items"),
        ]:
            rows = prepared[key]
            for r in rows:
                db.add(r)
            counts[key] = len(rows)

        attachment_rows: list[Attachment] = []
        if "attachments" in prepared:
            for r in prepared["attachments"]:
                db.add(r)
                attachment_rows.append(r)
            counts["attachments"] = len(attachment_rows)

        db.flush()

        # Now write attachment files after we know the rows are in.
        if attachment_files is not None and attachment_rows:
            base = DATA_DIR / "attachments"
            base.mkdir(parents=True, exist_ok=True)
            for att in attachment_rows:
                rel = att.stored_path  # e.g. "attachments/task/3/abcd.pdf"
                file_rel = rel.removeprefix("attachments/")
                if file_rel in attachment_files:
                    target = DATA_DIR / rel
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(attachment_files[file_rel])
                # If file is missing in zip, leave a gap (UI will 404 download).
                # Don't fail the whole restore for a missing attachment file.

        violations = db.execute(text("PRAGMA foreign_key_check")).all()
        if violations:
            detail = "; ".join(
                f"{row[0]} row {row[1]} -> {row[2]}" for row in violations[:10]
            )
            raise ValueError(f"备份包含无效关联: {detail}")
        db.commit()
        return counts
    except ValueError:
        db.rollback()
        raise
    except SQLAlchemyError as e:
        db.rollback()
        raise ValueError(f"备份数据无法写入: {e}") from e
    except Exception:
        db.rollback()
        raise
    finally:
        db.execute(text("PRAGMA foreign_keys = ON"))


def _dict_to_row(model, d: dict) -> object:
    """从 dict 重建 ORM 实例，忽略未知字段并恢复日期类型。"""
    columns = {c.name: c for c in model.__table__.columns}
    kwargs = {}
    for key, value in d.items():
        col = columns.get(key)
        if col is None:
            continue
        if value is not None and isinstance(value, str):
            if isinstance(col.type, DateTime):
                value = datetime.fromisoformat(value.removesuffix("Z"))
            elif isinstance(col.type, Date):
                value = date.fromisoformat(value)
        kwargs[key] = value
    if model is CostCategory:
        kwargs["is_builtin"] = False
    return model(**kwargs)
