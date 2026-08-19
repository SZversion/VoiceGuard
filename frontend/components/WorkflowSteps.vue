<script setup>
defineProps({
  current: {
    type: Number,
    default: 1
  }
})

const steps = [
  { number: 1, label: '통화 업로드' },
  { number: 2, label: '분석 진행' },
  { number: 3, label: '분석 결과' }
]
</script>

<template>
  <ol class="mx-auto mb-10 flex max-w-3xl items-start justify-between" aria-label="분석 진행 단계">
    <li v-for="(step, index) in steps" :key="step.number" class="flex flex-1 items-start last:flex-none">
      <div class="flex flex-col items-center">
        <span
          class="flex h-10 w-10 items-center justify-center rounded-full text-sm font-bold"
          :class="step.number <= current ? 'bg-blue-600 text-white' : 'bg-slate-200 text-slate-500'"
        >
          {{ step.number < current ? '✓' : step.number }}
        </span>
        <span
          class="mt-2 whitespace-nowrap text-xs font-semibold sm:text-sm"
          :class="step.number === current ? 'text-blue-600' : 'text-slate-500'"
        >
          {{ step.label }}
        </span>
      </div>
      <span
        v-if="index < steps.length - 1"
        class="mt-5 h-0.5 flex-1"
        :class="step.number < current ? 'bg-blue-600' : 'bg-slate-200'"
        aria-hidden="true"
      />
    </li>
  </ol>
</template>
