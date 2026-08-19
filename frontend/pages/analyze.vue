<template>
  <div>
    <WorkflowSteps :current="2" />
    <BaseCard>
      <h1 class="text-3xl font-extrabold text-slate-900">분석 진행</h1>
      <p class="mt-3 text-slate-500">분석 진행 화면은 3단계에서 완성합니다.</p>
      <p v-if="route.query.job_id" class="mt-4 text-sm text-slate-400">작업 번호: {{ route.query.job_id }}</p>
    </BaseCard>
  </div>
</template>

<script setup>
const route = useRoute()
</script>
