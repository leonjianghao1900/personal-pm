<template>
 <GlassCard class="p-8">
 <h2 class="text-2xl font-bold mb-4">📁 项目管理</h2>
 <button @click="onCreate" class="bg-apple-blue text-white px-4 py-2 rounded-lg font-medium">
 + 新建项目
 </button>
 <ul class="mt-4 space-y-2">
 <li v-for="p in projects.projects" :key="p.id"
 class="p-3 rounded-lg bg-white/60 dark:bg-white/[0.04] flex items-center justify-between">
 <div class="flex items-center gap-2 min-w-0 flex-1">
 <span class="w-3 h-3 rounded-full shrink-0" :style="{ background: p.color }"></span>
 <button @click="openEdit(p)" class="font-medium truncate text-left hover:text-apple-blue">
 {{ p.name }}
 </button>
 <span class="text-xs text-gray-500 dark:text-gray-400 shrink-0">{{ taskCount(p.id) }} 任务</span>
 </div>
 <div class="flex items-center gap-3 shrink-0">
 <button @click="goGantt(p.id)" class="text-apple-blue text-sm font-medium">甘特图 →</button>
 <button @click="openEdit(p)" class="text-gray-600 dark:text-gray-400 text-sm hover:text-apple-blue">编辑</button>
 <button @click="exportProject(p)" class="text-gray-600 dark:text-gray-400 text-sm hover:text-apple-blue">📥 Excel</button>
 <button @click="onRemove(p.id)" class="text-red-500 text-sm">删除</button>
 </div>
 </li>
 </ul>

 <ProjectPanel :open="showPanel" :project="editingProject"
 @close="showPanel = false"
 @saved="onSaved"
 @deleted="onSaved" />
 </GlassCard>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import GlassCard from '@/components/GlassCard.vue'
import ProjectPanel from '@/components/ProjectPanel.vue'
import { useProjectsStore } from '@/stores/projects'
import { useRouter } from 'vue-router'
import { projectsApi } from '@/api/client'
import { useTasksStore } from '@/stores/tasks'
import type { Project } from '@/api/types'

const projects = useProjectsStore()
const tasksStore = useTasksStore()
const router = useRouter()

const showPanel = ref(false)
const editingProject = ref<Project | null>(null)

async function onCreate() {
 editingProject.value = null
 showPanel.value = true
}

function openEdit(p: Project) {
 editingProject.value = p
 showPanel.value = true
}

function onSaved() {
 showPanel.value = false
 editingProject.value = null
}

async function onRemove(id: number) {
 if (!window.confirm('删除项目会级联删除其所有任务，确认？')) return
 await projects.remove(id)
}

function goGantt(projectId: number) {
 router.push('/gantt')
 projects.select(projectId)
}

function taskCount(projectId: number): number {
 return tasksStore.tasks.filter(t => t.project_id === projectId).length
}

async function exportProject(p: { id: number; name: string }) {
 try {
 await projectsApi.export(p.id, p.name)
 } catch {
 // axios interceptor handles errors
 }
}
</script>