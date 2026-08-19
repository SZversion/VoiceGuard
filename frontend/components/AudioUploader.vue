<script setup>
import { CloudArrowUpIcon, FolderOpenIcon } from '@heroicons/vue/24/outline'

const emit = defineEmits(['selected', 'error'])
const fileInput = ref(null)
const isDragging = ref(false)

const acceptedExtensions = ['wav', 'mp3', 'm4a']

function openFilePicker() {
  fileInput.value?.click()
}

function extensionOf(file) {
  return file.name.split('.').pop()?.toLowerCase() || ''
}

function validateAndEmit(file) {
  if (!file) return

  const extension = extensionOf(file)
  if (!acceptedExtensions.includes(extension)) {
    emit('error', '지원하지 않는 파일 형식입니다. WAV, MP3, M4A 파일을 선택해주세요.')
    return
  }

  emit('selected', file)
}

function onFileChange(event) {
  validateAndEmit(event.target.files?.[0])
  event.target.value = ''
}

function onDrop(event) {
  isDragging.value = false
  validateAndEmit(event.dataTransfer?.files?.[0])
}
</script>

<template>
  <div
    class="flex min-h-80 cursor-pointer flex-col items-center justify-center border-2 border-dashed p-8 text-center transition sm:min-h-96"
    :class="isDragging ? 'border-blue-500 bg-blue-50' : 'border-blue-200 bg-white hover:bg-blue-50/40'"
    role="button"
    tabindex="0"
    @click="openFilePicker"
    @keydown.enter.prevent="openFilePicker"
    @keydown.space.prevent="openFilePicker"
    @dragover.prevent="isDragging = true"
    @dragleave.prevent="isDragging = false"
    @drop.prevent="onDrop"
  >
    <input
      ref="fileInput"
      class="hidden"
      type="file"
      accept=".wav,.mp3,.m4a,audio/wav,audio/mpeg,audio/mp4"
      @change="onFileChange"
    />
    <CloudArrowUpIcon class="h-16 w-20 text-blue-600" aria-hidden="true" />
    <p class="mt-5 text-lg font-extrabold text-slate-800">파일을 여기로 드래그하거나 클릭하여 업로드</p>
    <p class="mt-2 text-sm text-slate-400">지원 형식: WAV, MP3, M4A</p>
    <div class="my-7 flex w-full max-w-md items-center gap-4 text-sm text-slate-400">
      <span class="h-px flex-1 bg-slate-200" />
      또는
      <span class="h-px flex-1 bg-slate-200" />
    </div>
    <button type="button" class="inline-flex items-center gap-2 border border-slate-200 bg-white px-6 py-3 text-sm font-bold text-blue-600 shadow-sm" @click.stop="openFilePicker">
      <FolderOpenIcon class="h-5 w-5" aria-hidden="true" />
      파일 선택
    </button>
  </div>
</template>
