<script setup>
import { XMarkIcon } from '@heroicons/vue/24/outline'

defineProps({
  file: {
    type: Object,
    default: null
  }
})

const emit = defineEmits(['remove'])

function formatBytes(bytes) {
  if (!bytes) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB']
  const index = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1)
  return `${(bytes / 1024 ** index).toFixed(index === 0 ? 0 : 1)} ${units[index]}`
}
</script>

<template>
  <div v-if="file" class="flex items-center gap-4 border border-slate-200 bg-white p-4">
    <span class="text-3xl text-blue-600" aria-hidden="true">♫</span>
    <div class="min-w-0 flex-1">
      <p class="truncate font-bold text-slate-800">{{ file.name }}</p>
      <p class="mt-1 text-sm text-slate-500">{{ formatBytes(file.size) }}</p>
    </div>
    <button
      type="button"
      class="shrink-0 rounded-md p-2 text-slate-400 transition hover:bg-red-50 hover:text-red-600 focus:outline-none focus:ring-2 focus:ring-red-300"
      aria-label="선택한 파일 제거"
      title="파일 제거"
      @click="emit('remove')"
    >
      <XMarkIcon class="h-5 w-5" aria-hidden="true" />
    </button>
  </div>
</template>
