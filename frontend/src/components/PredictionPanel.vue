<template>
  <div>
    <div class="flex items-center justify-between mb-4">
      <h3 class="text-lg font-bold text-slate-100">智能预测</h3>
      <div class="flex items-center gap-2">
        <select
          v-model="count"
          class="bg-white/10 border border-white/20 rounded-lg px-3 py-1.5 text-sm text-slate-100 outline-none"
        >
          <option :value="1" class="bg-slate-800">1 注</option>
          <option :value="3" class="bg-slate-800">3 注</option>
          <option :value="5" class="bg-slate-800">5 注</option>
        </select>
        <button
          @click="generate"
          :disabled="generating"
          class="px-4 py-1.5 rounded-lg bg-gradient-to-r from-violet-500 to-fuchsia-500 hover:from-violet-600 hover:to-fuchsia-600 text-sm font-bold text-white transition disabled:opacity-50"
        >
          {{ generating ? '生成中...' : '生成预测' }}
        </button>
      </div>
    </div>

    <!-- 分析说明 -->
    <div
      v-if="result?.analysis"
      class="mb-4 p-4 rounded-xl bg-white/5 border border-white/10 text-sm text-slate-300 leading-relaxed"
    >
      <div class="text-xs text-slate-500 mb-1">分析说明</div>
      {{ result.analysis }}
    </div>

    <!-- 预测结果 -->
    <div v-if="result?.predictions?.length" class="space-y-3 mb-6">
      <!-- 批量操作栏 -->
      <div
        v-if="result.predictions.length > 1"
        class="flex items-center justify-between gap-3 p-3 rounded-xl bg-white/5 border border-white/10"
      >
        <label class="flex items-center gap-2 cursor-pointer text-sm text-slate-300">
          <input
            type="checkbox"
            :checked="allSelected"
            @change="toggleAll($event.target.checked)"
            class="w-4 h-4 accent-violet-500"
          />
          全选 ({{ selectedCount }}/{{ result.predictions.length }})
        </label>
        <button
          @click="adoptSelected"
          :disabled="selectedCount === 0 || batchAdopting"
          class="px-4 py-1.5 rounded-lg bg-emerald-500 hover:bg-emerald-600 text-white text-xs font-bold transition disabled:opacity-50"
        >
          {{ batchAdopting ? `采纳中(${adoptProgress}/${selectedCount})...` : `采纳选中 (${selectedCount})` }}
        </button>
      </div>

      <div
        v-for="(pred, idx) in result.predictions"
        :key="idx"
        class="p-4 rounded-xl bg-gradient-to-br from-violet-500/10 to-fuchsia-500/10 border"
        :class="pred.selected ? 'border-violet-400/40' : 'border-violet-400/20'"
      >
        <div class="flex items-center justify-between mb-2">
          <label class="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              v-model="pred.selected"
              class="w-4 h-4 accent-violet-500"
            />
            <span class="text-xs text-slate-400">第 {{ idx + 1 }} 注</span>
          </label>
          <span
            class="text-[10px] px-2 py-0.5 rounded-full"
            :class="pred.used_llm ? 'bg-emerald-500/20 text-emerald-300' : 'bg-slate-500/20 text-slate-400'"
          >
            {{ pred.used_llm ? 'LLM' : '启发式' }}
          </span>
        </div>
        <BallDisplay :red-balls="pred.red_balls" :blue-balls="pred.blue_balls" />
        <div v-if="pred.reason" class="mt-2 text-xs text-slate-400 leading-relaxed">
          <span class="text-violet-300">理由：</span>{{ pred.reason }}
        </div>
        <button
          @click="adopt(pred)"
          :disabled="adoptingIdx === idx"
          class="mt-3 px-4 py-1.5 rounded-lg bg-violet-500 hover:bg-violet-600 text-white text-xs font-bold transition disabled:opacity-50"
        >
          {{ adoptingIdx === idx ? '采纳中...' : '采纳此号码' }}
        </button>
      </div>
    </div>

    <!-- 历史预测记录 -->
    <div v-if="history.length" class="mt-6">
      <div class="text-sm text-slate-400 mb-2">历史预测记录</div>
      <div class="overflow-x-auto rounded-xl border border-white/10">
        <table class="w-full text-sm">
          <thead>
            <tr class="bg-white/5 text-slate-300">
              <th class="px-3 py-2 text-left font-semibold">基于期号</th>
              <th class="px-3 py-2 text-left font-semibold">预测号码</th>
              <th class="px-3 py-2 text-left font-semibold">实际开奖</th>
              <th class="px-3 py-2 text-center font-semibold">命中</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="r in history"
              :key="r.id"
              class="border-t border-white/5 hover:bg-white/5"
            >
              <td class="px-3 py-2 text-slate-300 tabular-nums">{{ r.based_on_issue }}</td>
              <td class="px-3 py-2">
                <BallDisplay :red-balls="r.red_balls" :blue-balls="r.blue_balls" />
              </td>
              <td class="px-3 py-2">
                <span v-if="r.evaluated">
                  <BallDisplay :red-balls="r.actual_red_balls" :blue-balls="r.actual_blue_balls" />
                </span>
                <span v-else class="text-slate-600 text-xs">待开奖</span>
              </td>
              <td class="px-3 py-2 text-center">
                <span v-if="r.evaluated" class="font-bold tabular-nums" :class="hitClass(r)">
                  {{ r.red_hits }}+{{ r.blue_hits }}
                </span>
                <span v-else class="text-slate-600">-</span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { api } from '../api.js'
import { useToast } from '../composables/useToast.js'
import BallDisplay from './BallDisplay.vue'

const toast = useToast()
const count = ref(1)
const generating = ref(false)
const result = ref(null)
const history = ref([])
const adoptingIdx = ref(-1)
const batchAdopting = ref(false)
const adoptProgress = ref(0)

const selectedCount = computed(
  () => (result.value?.predictions || []).filter(p => p.selected).length,
)

const allSelected = computed(
  () => result.value?.predictions?.length > 0 && selectedCount.value === result.value.predictions.length,
)

function toggleAll(checked) {
  if (!result.value?.predictions) return
  result.value.predictions.forEach(p => { p.selected = checked })
}

async function adopt(pred) {
  adoptingIdx.value = result.value.predictions.indexOf(pred)
  try {
    const r = await api.adoptBet(
      pred.red_balls,
      pred.blue_balls,
      '',
      'ai_predict',
      pred.reason || '',
    )
    toast.success(r.message)
  } catch (e) {
    toast.error('采纳失败: ' + e.message)
  } finally {
    adoptingIdx.value = -1
  }
}

async function adoptSelected() {
  const picks = (result.value?.predictions || []).filter(p => p.selected)
  if (!picks.length) return
  batchAdopting.value = true
  adoptProgress.value = 0
  let success = 0
  let failed = 0
  for (const pred of picks) {
    try {
      await api.adoptBet(
        pred.red_balls,
        pred.blue_balls,
        '',
        'ai_predict',
        pred.reason || '',
      )
      success++
    } catch (e) {
      failed++
      console.error('采纳失败:', e.message)
    }
    adoptProgress.value++
  }
  batchAdopting.value = false
  if (success > 0) {
    toast.success(`成功采纳 ${success} 注` + (failed > 0 ? `（${failed} 注失败）` : ''))
  } else if (failed > 0) {
    toast.error(`采纳全部失败 (${failed} 注)`)
  }
}

async function generate() {
  generating.value = true
  try {
    result.value = await api.predict(count.value)
    if (result.value.error) {
      toast.error(result.value.error)
      result.value = null
    } else {
      // 为每注添加 selected 属性，默认全选
      result.value.predictions.forEach(p => { p.selected = true })
      toast.success('预测生成成功')
      loadHistory()
    }
  } catch (e) {
    toast.error('预测失败: ' + e.message)
  } finally {
    generating.value = false
  }
}

async function loadHistory() {
  try {
    history.value = await api.getPredictions(20)
  } catch {
    // ignore
  }
}

function hitClass(r) {
  const total = r.total_hits || 0
  if (total >= 5) return 'text-emerald-400'
  if (total >= 3) return 'text-amber-400'
  return 'text-slate-400'
}

onMounted(loadHistory)
</script>
