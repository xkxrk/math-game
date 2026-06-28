<template>
  <div class="w-full">
    <svg :viewBox="`0 0 ${W} ${H}`" class="w-full" style="height: 160px" preserveAspectRatio="none">
      <defs>
        <linearGradient :id="gradId" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="rgba(167,139,250,0.35)" />
          <stop offset="100%" stop-color="rgba(167,139,250,0)" />
        </linearGradient>
      </defs>
      <!-- 网格 -->
      <line v-for="i in 3" :key="'g'+i" :x1="0" :x2="W" :y1="(H/3)*i" :y2="(H/3)*i" stroke="rgba(255,255,255,0.05)" stroke-dasharray="3 3" />
      <!-- 填充区域 -->
      <polygon v-if="points" :points="`0,${H} ${points} ${W},${H}`" :fill="`url(#${gradId})`" />
      <!-- 折线 -->
      <polyline v-if="points" :points="points" fill="none" stroke="#a78bfa" stroke-width="2" stroke-linejoin="round" />
      <!-- 平均线 -->
      <line v-if="avgY != null" :x1="0" :x2="W" :y1="avgY" :y2="avgY" stroke="rgba(251,191,36,0.4)" stroke-dasharray="4 4" />
    </svg>
    <div class="flex justify-between text-[10px] text-slate-500 mt-1 tabular-nums">
      <span>最新 {{ lastVal ?? '-' }}</span>
      <span class="text-amber-400/70">均值 {{ avgVal ?? '-' }}</span>
      <span>最早 {{ firstVal ?? '-' }}</span>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  values: { type: Array, default: () => [] },
})

const W = 600
const H = 160
const gradId = 'sum-grad-' + Math.random().toString(36).slice(2, 8)

const points = computed(() => {
  const vals = props.values
  if (!vals.length) return ''
  const min = Math.min(...vals)
  const max = Math.max(...vals)
  const range = max - min || 1
  return vals.map((v, i) => {
    const x = vals.length === 1 ? W / 2 : (i / (vals.length - 1)) * W
    const y = H - ((v - min) / range) * (H - 20) - 10
    return `${x.toFixed(1)},${y.toFixed(1)}`
  }).join(' ')
})

const avgVal = computed(() => {
  if (!props.values.length) return null
  return (props.values.reduce((a, b) => a + b, 0) / props.values.length).toFixed(1)
})
const lastVal = computed(() => props.values[0] ?? null)
const firstVal = computed(() => props.values[props.values.length - 1] ?? null)

const avgY = computed(() => {
  if (!props.values.length || avgVal.value == null) return null
  const min = Math.min(...props.values)
  const max = Math.max(...props.values)
  const range = max - min || 1
  return H - ((Number(avgVal.value) - min) / range) * (H - 20) - 10
})
</script>
