<script setup>
defineProps({
  type: {
    type: String,
    default: 'button'
  },
  disabled: {
    type: Boolean,
    default: false
  },
  variant: {
    type: String,
    default: 'primary'
  }
})
</script>

<template>
  <button
    :type="type"
    :disabled="disabled"
    class="rounded-md px-5 py-3 text-sm font-bold transition disabled:cursor-not-allowed disabled:opacity-50"
    :class="variant === 'primary' ? 'bg-blue-600 text-white hover:bg-blue-700' : 'border border-slate-300 bg-white text-slate-700 hover:bg-slate-50'"
  >
    <slot />
  </button>
</template>
