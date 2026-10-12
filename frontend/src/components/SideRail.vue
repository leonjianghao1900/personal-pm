<template>
 <aside class="glass-card sticky top-5 p-3 flex flex-col items-center gap-1 self-start">
 <div class="w-12 h-12 rounded-2xl flex items-center justify-center text-2xl font-bold">
 <span class="bg-gradient-to-br from-apple-blue to-apple-purple bg-clip-text text-transparent">◉</span>
 </div>
 <div class="w-8 h-px bg-black/10 dark:bg-white/10 my-1"></div>
 <RailIcon v-for="item in mainItems" :key="item.path" :to="item.path" :icon="item.icon"
 :active="isActive(item.path)" :title="item.label" />
 <div class="w-8 h-px bg-black/10 dark:bg-white/10 my-1"></div>
 <RailIcon to="/settings" icon="⚙" title="系统管理" />
 </aside>
</template>

<script setup lang="ts">
import { useRoute } from 'vue-router'
import RailIcon from './RailIcon.vue'

const route = useRoute()
const mainItems = [
 { path: '/dashboard', icon: '📊', label: '总览仪表盘' },
 { path: '/gantt', icon: '📅', label: '甘特图' },
 { path: '/tasks', icon: '✅', label: '任务管理' },
 { path: '/costs', icon: '💰', label: '费用记录' },
 { path: '/inbox', icon: '📥', label: '临时收件箱' }
]

function isActive(path: string) {
 return route.path === path || route.path.startsWith(path + '/')
}
</script>
