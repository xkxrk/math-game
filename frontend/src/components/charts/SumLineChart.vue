<template>
  <!-- 简易 SVG 折线图：和值走势 -->
  <div v-if="values && values.length" class="w-full">
    <svg :viewBox="`0 0 ${width} ${height}`" class="w-full" preserveAspectRatio="none">
      <!-- 网格线 -->
      <line v-for="g in gridLines" :key="g" :x1="0" :x2="width" :y1="g" :y2="g" stroke="rgba(255,255,255,0.05)" stroke-width="1" />
      <!-- 平均线 -->
      <line :x1="0" :x2="width" :y1="avgY" :y2="avgY" stroke="rgba(245,158,11,0.5)" stroke-width="1" stroke-dasharray="4 4" />
      <!-- 折线 -->
      <polyline
        :points="linePoints"
        fill="none"
        stroke="url(#sumGradient)"
        stroke-width="2"
        stroke-linecap="round"
        stroke-linejoin="round"
      />
      <!-- 渐变定义 -->
      <defs>
        <linearGradient id="sumGradient" x1="0%" y1="0%" x2="100%" y2="0%">
          <stop offset="0%" stop-color="#8b5cf6" />
          <stop offset="100%" stop-color="#d946ef" />
        </linearGradient>
      </defs>
      <!-- 点 -->
      <circle
        v-for="(p, i) in points"
        :key="i"
        :cx="p.x"
        :cy="p.y"
        r="2"
        :fill="i === 0 ? '#d946ef' : '#8b5cf6'"
      />
    </svg>
    <!-- X 轴标签 -->
    <div class="flex justify-between text-[10px] text-slate-500 mt-1">
      <span>最新 {{ values[0] }}</span>
      <span>第 {{ Math.ceil(values.length / 2) }} 期</span>
      <span>最早 {{ values[values.length - 1] }}</span>
    </div>
    <div class="text-[10px] text-slate-500 text-center mt-1">
      平均线: <span class="text-amber-400 font-bold">{{ avgValue.toFixed(1) }}</span>
    </div>
  </div>
  <div v-else class="text-center text-xs text-slate-500 py-8">暂无数据</div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  values: { type: Array, default: () => [] },
})

const width = 600
const height = 120
const padding = 10

const validValues = computed(() => props.values.filter(v => v != null))
const minVal = computed(() => Math.min(...validValues.value))
const maxVal = computed(() => Math.max(...validValues.value))
const avgValue = computed(() => {
  if (!validValues.value.length) return 0
  return validValues.value.reduce((a, b) => a + b, 0) / validValues.value.length
})

const range = computed(() => Math.max(maxVal.value - minVal.value, 1))

const points = computed(() => {
  const n = props.values.length
  if (n === 0) return []
  return props.values.map((v, i) => {
    const x = padding + (i / Math.max(n - 1, 1)) * (width - 2 * padding)
    const y = height - padding - ((v - minVal.value) / range.value) * (height - 2 * padding)
    return { x, y }
  })
})

const linePoints = computed(() => points.value.map(p => `${p.x},${p.y}`).join(' '))

const gridLines = computed(() => {
  const lines = []
  for (let i = 0; i <= 4; i++) {
    lines.push(padding + (i / 4) * (height - 2 * padding))
  }
  return lines
})

const avgY = computed(() => {
  return height - padding - ((avgValue.value - minVal.value) / range.value) * (height - 2 * padding)
})
</script>
