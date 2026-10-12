; Inno Setup script for Personal PM
; Generates: installer\PersonalPM-Setup-0.1.0.exe
;
; Default install: %LOCALAPPDATA%\Programs\PersonalPM\ (no admin required)
; User data lives next to the exe ({app}\data\) — auto-created on first run.

[Setup]
AppId={{A7A87AA9-389D-495F-9C71-CE189B3281A7}
AppName=Personal PM
AppVersion=0.2.0
AppPublisher=leonkangxi-dev
DefaultDirName={localappdata}\Programs\PersonalPM
DefaultGroupName=Personal PM
DisableProgramGroupPage=yes
OutputBaseFilename=PersonalPM-Setup-0.2.0
OutputDir=installer
Compression=lzma2
SolidCompression=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
Uninstallable=yes
UninstallDisplayIcon={app}\personal-pm.exe

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Files]
Source: "dist\personal-pm.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Personal PM"; Filename: "{app}\personal-pm.exe"
Name: "{group}\卸载 Personal PM"; Filename: "{uninstallexe}"
Name: "{userdesktop}\Personal PM"; Filename: "{app}\personal-pm.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "在桌面创建快捷方式"; GroupDescription: "附加选项"

[Run]
Filename: "{app}\personal-pm.exe"; Description: "启动 Personal PM"; Flags: nowait postinstall skipifsilent runascurrentuser
