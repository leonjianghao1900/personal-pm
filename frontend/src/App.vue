<template>
 <div class="max-w-[1500px] mx-auto p-5 grid grid-cols-[72px_1fr] gap-4 min-h-screen">
 <SideRail />
 <div class="flex flex-col gap-4">
 <TopBar />
 <RouterView />
 </div>
 </div>
 <UpdateBanner />
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import SideRail from '@/components/SideRail.vue'
import TopBar from '@/components/TopBar.vue'
import UpdateBanner from '@/components/UpdateBanner.vue'
import { useProjectsStore } from '@/stores/projects'

const projects = useProjectsStore()

onMounted(() => {
 projects.fetchAll()
})
</script>
