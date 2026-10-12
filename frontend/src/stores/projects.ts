import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { projectsApi } from '@/api/client'
import type { Project } from '@/api/types'

export const useProjectsStore = defineStore('projects', () => {
  const projects = ref<Project[]>([])
  const currentId = ref<number | null>(null)

  const current = computed(() =>
    projects.value.find(p => p.id === currentId.value) ?? null
  )

  const byId = computed(() => {
    const m = new Map<number, Project>()
    projects.value.forEach(p => m.set(p.id, p))
    return m
  })

  async function fetchAll() {
    projects.value = await projectsApi.list()
    if (currentId.value === null && projects.value.length > 0) {
      currentId.value = projects.value[0].id
    }
  }

  async function create(data: { name: string; color?: string }) {
    const p = await projectsApi.create(data)
    projects.value.push(p)
    currentId.value = p.id
    return p
  }

  async function remove(id: number) {
    await projectsApi.remove(id)
    projects.value = projects.value.filter(p => p.id !== id)
    if (currentId.value === id) {
      currentId.value = projects.value[0]?.id ?? null
    }
  }

  function select(id: number) {
    currentId.value = id
  }

  return { projects, currentId, current, byId, fetchAll, create, remove, select }
})
