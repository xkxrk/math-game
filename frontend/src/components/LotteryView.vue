<template>
  <div>
    <!-- 标签栏 -->
    <div class="flex flex-wrap gap-2 mb-6 p-1 rounded-xl bg-white/5 border border-white/10">
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

    <!-- 内容区 -->
    <div class="rounded-2xl bg-white/5 backdrop-blur border border-white/10 shadow-xl p-4 sm:p-6">
      <HistoryTable v-show="active === 'history'" ref="historyRef" />
      <PredictionPanel v-show="active === 'predict'" />
      <BacktestPanel v-show="active === 'backtest'" />
      <MyBetsPanel v-show="active === 'mybets'" ref="myBetsRef" />
      <AnalysisPanel v-show="active === 'analyze'" />
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import HistoryTable from './HistoryTable.vue'
import PredictionPanel from './PredictionPanel.vue'
import BacktestPanel from './BacktestPanel.vue'
import MyBetsPanel from './MyBetsPanel.vue'
import AnalysisPanel from './AnalysisPanel.vue'

const active = ref('history')
const historyRef = ref(null)
const myBetsRef = ref(null)

const tabs = [
  { id: 'history', name: '开奖历史' },
  { id: 'predict', name: '智能预测' },
  { id: 'backtest', name: '回测模拟' },
  { id: 'mybets', name: '我的投注' },
  { id: 'analyze', name: '号码分析' },
]
</script>
