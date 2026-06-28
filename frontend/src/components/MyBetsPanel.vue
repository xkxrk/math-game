<template>
  <div class="flex flex-col h-full min-h-0">
    <!-- 汇总卡片 -->
    <div class="grid grid-cols-2 md:grid-cols-5 gap-3 mb-6 shrink-0">
      <div class="p-3 rounded-xl bg-white/5 border border-white/10 text-center">
        <div class="text-xs text-slate-400">总投注</div>
        <div class="text-xl font-bold text-slate-200">{{ summary.total_bets }}</div>
      </div>
      <div class="p-3 rounded-xl bg-white/5 border border-white/10 text-center">
        <div class="text-xs text-slate-400">总花费</div>
        <div class="text-xl font-bold text-slate-200">{{ summary.total_cost }}元</div>
      </div>
      <div class="p-3 rounded-xl bg-white/5 border border-white/10 text-center">
        <div class="text-xs text-slate-400">总中奖</div>
        <div class="text-xl font-bold text-amber-300">{{ formatMoney(summary.total_winnings) }}</div>
      </div>
      <div
        class="p-3 rounded-xl border text-center"
        :class="summary.net_profit >= 0 ? 'bg-emerald-500/10 border-emerald-400/20' : 'bg-red-500/10 border-red-400/20'"
      >
        <div class="text-xs text-slate-400">净收益</div>
        <div
          class="text-xl font-bold"
          :class="summary.net_profit >= 0 ? 'text-emerald-300' : 'text-red-300'"
        >
          {{ summary.net_profit >= 0 ? '+' : '' }}{{ formatMoney(summary.net_profit) }}
        </div>
      </div>
      <div class="p-3 rounded-xl bg-white/5 border border-white/10 text-center">
        <div class="text-xs text-slate-400">中奖率</div>
        <div class="text-xl font-bold text-slate-200">{{ summary.win_rate }}%</div>
        <div class="text-[10px] text-slate-500">{{ summary.won_count }}/{{ summary.evaluated_count }}期</div>
      </div>
    </div>

    <!-- 操作栏 -->
    <div class="flex flex-wrap items-center justify-between gap-3 mb-4 shrink-0">
      <div class="flex flex-wrap items-center gap-2">
        <!-- 状态筛选 -->
        <button
          v-for="f in filters"
          :key="f.id"
          @click="filter = f.id; load()"
          :class="[
            'px-3 py-1.5 rounded-lg text-sm transition',
            filter === f.id ? 'bg-violet-500 text-white' : 'bg-white/10 text-slate-300 hover:bg-white/20',
          ]"
        >
          {{ f.name }}
          <span v-if="f.count !== null" class="ml-1 text-xs opacity-70">({{ f.count }})</span>
        </button>

        <!-- 模型筛选 -->
        <div class="flex items-center gap-2 ml-2">
          <span class="text-xs text-slate-400">模型:</span>
          <USelect
            v-model="modelFilter"
            :options="betModelOptions"
            placeholder="全部模型"
            @change="load"
            class="w-[160px]"
          />
        </div>
      </div>
      <button
        @click="evaluate"
        :disabled="evaluating"
        class="px-4 py-1.5 rounded-lg bg-white/10 hover:bg-white/20 text-sm text-slate-100 transition disabled:opacity-50"
      >
        {{ evaluating ? '评估中...' : '评估待开奖' }}
      </button>
    </div>

    <!-- 投注列表 -->
    <div class="flex-1 min-h-0 overflow-y-auto overflow-x-hidden space-y-3 pr-1">
      <div
        v-for="bet in bets"
        :key="bet.id"
        class="p-4 rounded-xl border transition"
        :class="bet.evaluated ? (bet.prize_level > 0 ? 'bg-amber-500/5 border-amber-400/20' : 'bg-slate-500/5 border-slate-400/10') : 'bg-violet-500/5 border-violet-400/20'"
      >
        <div class="flex items-start justify-between gap-3">
          <div class="flex-1">
            <!-- 号码 -->
            <BallDisplay :red-balls="bet.red_balls" :blue-balls="bet.blue_balls" />

            <!-- 元信息 -->
            <div class="flex flex-wrap items-center gap-3 mt-2 text-xs text-slate-400">
              <span>目标期号: <strong class="text-slate-300">{{ bet.target_issue }}</strong></span>
              <span v-if="bet.source === 'ai_predict'" class="px-2 py-0.5 rounded-full bg-violet-500/20 text-violet-300">AI预测</span>
              <span v-else-if="bet.source === 'backtest'" class="px-2 py-0.5 rounded-full bg-blue-500/20 text-blue-300">回测</span>
              <span v-else class="px-2 py-0.5 rounded-full bg-slate-500/20 text-slate-400">手动</span>
              <span
                v-if="bet.llm_model"
                class="px-2 py-0.5 rounded-full bg-fuchsia-500/20 text-fuchsia-300"
                :title="`预测模型: ${bet.llm_model}`"
              >
                {{ bet.llm_model }}
              </span>
              <span>花费: {{ bet.cost }}元</span>
              <span v-if="bet.created_at">{{ formatTime(bet.created_at) }}</span>
            </div>

            <!-- 理由 -->
            <div v-if="bet.reason" class="mt-1 text-xs text-slate-500">
              <span class="text-violet-300">理由：</span>{{ bet.reason }}
            </div>

            <!-- 评估结果 -->
            <div v-if="bet.evaluated" class="mt-3 flex flex-wrap items-center gap-3">
              <span class="text-xs text-slate-400">实际开奖:</span>
              <BallDisplay :red-balls="bet.actual_red_balls" :blue-balls="bet.actual_blue_balls" />
              <span class="text-xs text-slate-400">
                命中: <strong :class="bet.prize_level > 0 ? 'text-amber-300' : 'text-slate-500'">{{ bet.red_hits }}+{{ bet.blue_hits }}</strong>
              </span>
              <span
                class="px-3 py-1 rounded-full text-xs font-bold"
                :class="prizeBadgeClass(bet.prize_level)"
              >
                {{ bet.prize_desc }}
                <span v-if="bet.prize_amount > 0"> · {{ formatMoney(bet.prize_amount) }}</span>
              </span>
            </div>
            <div v-else class="mt-3 text-xs text-violet-300">
              待开奖...
            </div>
          </div>

          <!-- 删除按钮 -->
          <button
            @click="remove(bet.id)"
            class="text-slate-500 hover:text-red-400 transition text-sm"
            title="删除"
          >
            删除
          </button>
        </div>
      </div>

      <div v-if="!bets.length" class="text-center py-12 text-slate-500">
        暂无投注记录，去「智能预测」生成号码后点击「采纳」
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { api } from '../api.js'
import { useToast } from '../composables/useToast.js'
import BallDisplay from './BallDisplay.vue'
import USelect from './USelect.vue'

const toast = useToast()
const bets = ref([])
const betModels = ref([])
const betModelOptions = computed(() => [
  { value: '', label: '全部模型' },
  ...betModels.value.map(m => ({ value: m, label: m })),
])
const modelFilter = ref('')
const summary = ref({
  total_bets: 0,
  total_cost: 0,
  total_winnings: 0,
  net_profit: 0,
  evaluated_count: 0,
  pending_count: 0,
  won_count: 0,
  win_rate: 0,
})
const filter = ref('all')
const evaluating = ref(false)

const filters = ref([
  { id: 'all', name: '全部', count: null },
  { id: 'pending', name: '待开奖', count: null },
  { id: 'evaluated', name: '已评估', count: null },
])

async function loadBetModels() {
  try {
    const r = await api.getBetModels()
    betModels.value = r.models || []
  } catch {
    // ignore
  }
}

async function load() {
  try {
    const [betsData, summaryData] = await Promise.all([
      api.getBets(filter.value, modelFilter.value),
      api.getBetsSummary(),
    ])
    bets.value = betsData
    summary.value = summaryData
    // 更新筛选器计数
    filters.value[0].count = summaryData.total_bets
    filters.value[1].count = summaryData.pending_count
    filters.value[2].count = summaryData.evaluated_count
  } catch (e) {
    toast.error('加载失败: ' + e.message)
  }
}

async function evaluate() {
  evaluating.value = true
  try {
    const r = await api.evaluateBets()
    toast.success(r.message)
    await load()
  } catch (e) {
    toast.error('评估失败: ' + e.message)
  } finally {
    evaluating.value = false
  }
}

async function remove(id) {
  try {
    await api.deleteBet(id)
    toast.success('已删除')
    await Promise.all([load(), loadBetModels()])
  } catch (e) {
    toast.error('删除失败: ' + e.message)
  }
}

function formatMoney(n) {
  if (n >= 1_0000_0000) return (n / 1_0000_0000).toFixed(2) + '亿'
  if (n >= 1_0000) return (n / 1_0000).toFixed(1) + '万'
  return n + '元'
}

function formatTime(s) {
  if (!s) return ''
  return s.slice(0, 16).replace('T', ' ')
}

function prizeBadgeClass(level) {
  if (!level || level === 0) return 'bg-slate-500/20 text-slate-400'
  if (level <= 2) return 'bg-amber-500/20 text-amber-300'
  if (level <= 4) return 'bg-violet-500/20 text-violet-300'
  return 'bg-emerald-500/20 text-emerald-300'
}

function onDataUpdated() {
  load()
  loadBetModels()
}

onMounted(() => {
  loadBetModels()
  load()
  window.addEventListener('lottery-data-updated', onDataUpdated)
})
onUnmounted(() => {
  window.removeEventListener('lottery-data-updated', onDataUpdated)
})
defineExpose({ load })
</script>
