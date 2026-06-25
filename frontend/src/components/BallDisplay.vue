<template>
  <div class="inline-flex items-center gap-1.5 flex-wrap">
    <span
      v-for="ball in reds"
      :key="`r-${ball}`"
      class="inline-flex items-center justify-center w-8 h-8 rounded-full text-white text-sm font-bold shadow-md"
      :class="redClass"
    >
      {{ ball }}
    </span>
    <span v-if="blues.length" class="mx-1 text-slate-500">|</span>
    <span
      v-for="ball in blues"
      :key="`b-${ball}`"
      class="inline-flex items-center justify-center w-8 h-8 rounded-full text-white text-sm font-bold shadow-md"
      :class="blueClass"
    >
      {{ ball }}
    </span>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  redBalls: { type: [Array, String], default: () => [] },
  blueBalls: { type: [Array, String], default: () => [] },
  size: { type: String, default: 'md' },
})

const reds = computed(() => normalize(props.redBalls))
const blues = computed(() => normalize(props.blueBalls))

function normalize(val) {
  if (!val) return []
  if (Array.isArray(val)) return val
  return String(val).split(',').map((s) => s.trim()).filter(Boolean)
}

const redClass = computed(() => ({
  'bg-gradient-to-br from-red-500 to-red-600': true,
}))
const blueClass = computed(() => ({
  'bg-gradient-to-br from-blue-500 to-blue-600': true,
}))
</script>
