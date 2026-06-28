<template>
  <div class="flex flex-col h-full min-h-0">
    <!-- 顶部栏：标签 + 设置按钮 -->
    <div class="flex items-center gap-2 mb-4 shrink-0">
      <div class="flex-1 flex flex-wrap gap-2 p-1 rounded-xl bg-white/5 border border-white/10">
        <button
          v-for="tab in tabs"
          :key="tab.id"
          @click="active = tab.id"
          :class="[
            'flex-1 min-w-[80px] px-4 py-2 rounded-lg text-sm font-bold transition',
            active === tab.id
              ? 'bg-white text-slate-900 shadow'
              : 'text-slate-300 hover:bg-white/10',
          ]"
        >
          {{ tab.name }}
        </button>
      </div>
      <button
        @click="settingsVisible = true"
        title="模型设置"
        class="shrink-0 w-10 h-10 flex items-center justify-center rounded-xl bg-white/5 border border-white/10 text-slate-300 hover:bg-white/10 hover:text-slate-100 transition"
      >
        <svg class="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="12" cy="12" r="3" />
          <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09a1.65 1.65 0 0 0-1-1.51 1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09a1.65 1.65 0 0 0 1.51-1 1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33h0a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51h0a1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82v0a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" />
        </svg>
      </button>
    </div>

    <!-- 内容区 -->
    <div class="rounded-2xl bg-white/5 backdrop-blur border border-white/10 shadow-xl p-4 sm:p-6 flex-1 min-h-0 overflow-hidden">
      <HistoryTable v-show="active === 'history'" ref="historyRef" />
      <PredictionPanel v-show="active === 'predict'" />
      <BacktestPanel v-show="active === 'backtest'" />
      <MyBetsPanel v-show="active === 'mybets'" ref="myBetsRef" />
      <AnalysisPanel v-show="active === 'analyze'" ref="analysisRef" />
    </div>

    <!-- 模型设置弹窗 -->
    <SettingsModal
      :visible="settingsVisible"
      @close="settingsVisible = false"
      @saved="onSettingsSaved"
    />
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import HistoryTable from './HistoryTable.vue'
import PredictionPanel from './PredictionPanel.vue'
import BacktestPanel from './BacktestPanel.vue'
import MyBetsPanel from './MyBetsPanel.vue'
import AnalysisPanel from './AnalysisPanel.vue'
import SettingsModal from './SettingsModal.vue'

const active = ref('history')
const historyRef = ref(null)
const myBetsRef = ref(null)
const analysisRef = ref(null)
const settingsVisible = ref(false)

watch(active, (v) => {
  if (v === 'analyze') analysisRef.value?.refresh()
})

const tabs = [
  { id: 'history', name: '开奖历史' },
  { id: 'predict', name: '智能预测' },
  { id: 'backtest', name: '回测模拟' },
  { id: 'mybets', name: '我的投注' },
  { id: 'analyze', name: '号码分析' },
]

function onSettingsSaved() {
  // 保存后可在此触发刷新，当前各面板按需自取最新配置，无需特殊处理
}
</script>
