<template>
  <div class="w-full">
    <svg :viewBox="`0 0 ${W} ${H}`" class="w-full" style="height: 160px" preserveAspectRatio="none">
      <defs>
        <linearGradient :id="gradId" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="rgba(251,191,36,0.35)" />
          <stop offset="100%" stop-color="rgba(251,191,36,0)" />
        </linearGradient>
      </defs>
      <line v-for="i in 3" :key="'g'+i" :x1="0" :x2="W" :y1="(H/3)*i" :y2="(H/3)*i" stroke="rgba(255,255,255,0.05)" stroke-dasharray="3 3" />
      <polygon v-if="points" :points="`0,${H} ${points} ${W},${H}`" :fill="`url(#${gradId})`" />
      <polyline v-if="points" :points="points" fill="none" stroke="#fbbf24" stroke-width="2" stroke-linejoin="round" />
      <!-- 8亿阈值线 -->
      <line v-if="thresholdY != null" :x1="0" :x2="W" :y1="thresholdY" :y2="thresholdY" stroke="rgba(52,211,153,0.4)" stroke-dasharray="4 4" />
    </svg>
    <div class="flex justify-between text-[10px] text-slate-500 mt-1 tabular-nums">
      <span>最新 {{ lastLabel }}</span>
      <span class="text-emerald-400/70">阈值 8亿</span>
      <span>最早 {{ firstLabel }}</span>
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
const gradId = 'pool-grad-' + Math.random().toString(36).slice(2, 8)

const toY = (v, min, max) => {
  const range = max - min || 1
  return H - ((v - min) / range) * (H - 20) - 10
}

const points = computed(() => {
  const vals = props.values
  if (!vals.length) return ''
  const min = Math.min(...vals)
  const max = Math.max(...vals)
  return vals.map((v, i) => {
    const x = vals.length === 1 ? W / 2 : (i / (vals.length - 1)) * W
    const y = toY(v, min, max)
    return `${x.toFixed(1)},${y.toFixed(1)}`
  }).join(' ')
})

const thresholdY = computed(() => {
  const vals = props.values
  if (!vals.length) return null
  const min = Math.min(...vals)
  const max = Math.max(...vals)
  return toY(8_0000_0000, min, max)
})

const fmt = (v) => v == null ? '-' : (v / 1_0000_0000).toFixed(2) + '亿'
const lastLabel = computed(() => fmt(props.values[0]))
const firstLabel = computed(() => fmt(props.values[props.values.length - 1]))
</script>
