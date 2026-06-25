<template>
  <div class="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-800 text-slate-100">
    <div class="mx-auto max-w-5xl px-4 sm:px-6 py-6 sm:py-10">
      <!-- 头部 -->
      <div class="mb-6 sm:mb-8">
        <div class="flex flex-col items-center gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div class="flex items-center justify-center sm:justify-start gap-3">
            <img src="/favicon.svg" alt="Logo" class="w-11 h-11 drop-shadow-[0_0_15px_rgba(239,68,68,0.5)]" />
            <div>
              <div class="text-2xl sm:text-3xl font-extrabold tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-red-500 to-blue-500">
                超级大乐透预测辅助
              </div>
              <div class="text-xs text-slate-400 mt-0.5">前区 35 选 5 · 后区 12 选 2 · 周一/三/六开奖</div>
            </div>
          </div>
          <div class="flex flex-col items-center sm:items-end">
            <div class="flex items-center gap-2 text-[11px] text-slate-400">
              <span class="w-2 h-2 rounded-full bg-emerald-400 shadow-[0_0_14px_rgba(52,211,153,0.55)]"></span>
              <span>北京时间</span>
            </div>
            <div class="mt-1 text-2xl sm:text-[28px] leading-none font-extrabold tabular-nums tracking-wide">
              {{ timeText }}
            </div>
            <div class="mt-1 text-xs text-slate-400 tabular-nums">{{ dateText }}</div>
          </div>
        </div>
        <div class="mt-3 text-xs text-slate-500 text-center sm:text-left">
          提示：彩票具有随机性，内容仅供娱乐与研究参考
        </div>
      </div>

      <!-- 主体 -->
      <LotteryView />
    </div>

    <Toast ref="toastRef" />
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import LotteryView from './components/LotteryView.vue'
import Toast from './components/Toast.vue'
import { setToastInstance } from './composables/useToast.js'

const toastRef = ref(null)
const now = ref(new Date())
let nowTimer = null

const dateText = computed(() =>
  now.value.toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    weekday: 'short',
  })
)

const timeText = computed(() =>
  now.value.toLocaleTimeString('zh-CN', {
    hour12: false,
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  })
)

onMounted(() => {
  if (toastRef.value) setToastInstance(toastRef.value)
  nowTimer = window.setInterval(() => {
    now.value = new Date()
  }, 1000)
})

onBeforeUnmount(() => {
  if (nowTimer) window.clearInterval(nowTimer)
})
</script>
