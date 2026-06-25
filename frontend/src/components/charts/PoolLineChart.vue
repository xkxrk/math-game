<template>
  <!-- 简易 SVG 折线图：奖池趋势（单位：亿元） -->
  <div v-if="values && values.length" class="w-full">
    <svg :viewBox="`0 0 ${width} ${height}`" class="w-full" preserveAspectRatio="none">
      <!-- 8亿阈值线 -->
      <line :x1="0" :x2="width" :y1="thresholdY" :y2="thresholdY" stroke="rgba(245,158,11,0.4)" stroke-width="1" stroke-dasharray="4 4" />
      <text :x="width - 60" :y="thresholdY - 4" font-size="9" fill="rgba(245,158,11,0.7)">8亿阈值</text>
      <!-- 折线 -->
      <polyline
        :points="linePoints"
        fill="none"
        stroke="url(#poolGradient)"
        stroke-width="2"
        stroke-linecap="round"
        stroke-linejoin="round"
      />
      <defs>
        <linearGradient id="poolGradient" x1="0%" y1="0%" x2="100%" y2="0%">
          <stop offset="0%" stop-color="#10b981" />
          <stop offset="100%" stop-color="#06b6d4" />
        </linearGradient>
      </defs>
      <!-- 点 -->
      <circle
        v-for="(p, i) in points"
        :key="i"
        :cx="p.x"
        :cy="p.y"
        r="2"
        :fill="p.y < thresholdY ? '#f59e0b' : '#10b981'"
      />
    </svg>
    <div class="flex justify-between text-[10px] text-slate-500 mt-1">
      <span>最新</span>
      <span>最早</span>
    </div>
  </div>
  <div v-else class="text-center text-xs text-slate-500 py-8">暂无奖池数据</div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  values: { type: Array, default: () => [] },  // 单位：元
})

const width = 600
const height = 140
const padding = 10
const POOL_THRESHOLD = 8_0000_0000  // 8亿

const validValues = computed(() => props.values.filter(v => v != null))
const minVal = computed(() => Math.min(...validValues.value, POOL_THRESHOLD * 0.5))
const maxVal = computed(() => Math.max(...validValues.value, POOL_THRESHOLD * 1.2))
const range = computed(() => Math.max(maxVal.value - minVal.value, 1))

const points = computed(() => {
  const n = props.values.length
  if (n === 0) return []
  return props.values.map((v, i) => {
    const x = padding + (i / Math.max(n - 1, 1)) * (width - 2 * padding)
    const safeV = v != null ? v : minVal.value
    const y = height - padding - ((safeV - minVal.value) / range.value) * (height - 2 * padding)
    return { x, y }
  })
})

const linePoints = computed(() => points.value.map(p => `${p.x},${p.y}`).join(' '))

const thresholdY = computed(() => {
  return height - padding - ((POOL_THRESHOLD - minVal.value) / range.value) * (height - 2 * padding)
})
</script>
