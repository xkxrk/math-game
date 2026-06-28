<template>
  <div class="flex flex-col h-full min-h-0">
    <div class="flex flex-wrap items-center justify-between gap-3 mb-4 shrink-0">
      <h3 class="text-lg font-bold text-slate-100">智能预测</h3>
      <div class="flex flex-wrap items-center gap-2">
        <ModelSelector v-model="selectedModels" />
        <USelect
          v-model="count"
          :options="[{value:1,label:'1 注'},{value:3,label:'3 注'},{value:5,label:'5 注'}]"
          class="w-[90px]"
        />
        <button
          @click="generate"
          :disabled="generating"
          class="px-4 py-2 rounded-lg bg-gradient-to-r from-violet-500 to-fuchsia-500 hover:from-violet-600 hover:to-fuchsia-600 text-sm font-bold text-white transition disabled:opacity-50"
        >
          {{ generating ? '生成中...' : '生成预测' }}
        </button>
        <button
          v-if="result"
          @click="resetPredictions"
          class="px-4 py-2 rounded-lg bg-white/10 hover:bg-white/20 text-slate-300 text-sm font-bold transition"
        >
          重置
        </button>
      </div>
    </div>

    <div class="flex-1 min-h-0 overflow-y-auto overflow-x-hidden pr-1">
    <!-- ========== 单模型结果（向后兼容） ========== -->
    <template v-if="result && !result.multi">
      <!-- 分析说明 -->
      <div
        v-if="result?.analysis"
        class="mb-4 p-4 rounded-xl bg-white/5 border border-white/10 text-sm text-slate-300 leading-relaxed"
      >
        <div class="text-xs text-slate-500 mb-1 flex items-center gap-2">
          <span>分析说明</span>
          <span
            v-if="result.meta?.model"
            class="px-2 py-0.5 rounded-full bg-fuchsia-500/20 text-fuchsia-300"
          >{{ result.meta.model }}</span>
        </div>
        {{ result.analysis }}
      </div>

      <!-- 预测结果 -->
      <div v-if="result?.predictions?.length" class="space-y-3 mb-6">
        <BatchBar
          :predictions="result.predictions"
          :all-selected="allSelected"
          :selected-count="selectedCount"
          :batch-adopting="batchAdopting"
          :adopt-progress="adoptProgress"
          @toggle-all="toggleAll"
          @adopt-selected="adoptSelected"
        />

        <div
          v-for="(pred, idx) in result.predictions"
          :key="idx"
          class="p-4 rounded-xl bg-gradient-to-br from-violet-500/10 to-fuchsia-500/10 border"
          :class="pred.selected ? 'border-violet-400/40' : 'border-violet-400/20'"
        >
          <PredictionCard
            :pred="pred"
            :idx="idx"
            :adopting="adoptingIdx === idx"
            :model="result.meta?.model || ''"
            @toggle="pred.selected = !pred.selected"
            @adopt="adopt(pred, result.meta?.model || '')"
          />
        </div>
      </div>
    </template>

    <!-- ========== 多模型结果 ========== -->
    <template v-if="result && result.multi">
      <!-- 二次预测排序操作栏 -->
      <div class="mb-4 p-3 rounded-xl bg-gradient-to-r from-amber-500/10 to-fuchsia-500/10 border border-amber-400/20">
        <div class="flex flex-wrap items-center gap-2">
          <span class="text-sm text-slate-100 font-semibold flex items-center gap-1.5">
            <svg class="w-4 h-4 text-amber-300" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M9 11H5a2 2 0 0 0-2 2v7h6v-7a2 2 0 0 1 2-2h0"/>
              <path d="M15 11h4a2 2 0 0 1 2 2v7h-6v-7a2 2 0 0 0-2-2h0"/>
              <path d="M12 2v20"/>
            </svg>
            二次预测排序
          </span>
          <USelect
            v-model="rankModel"
            :options="rankModelOptions"
            placeholder="选评审模型"
            class="w-[180px]"
          />
          <button
            @click="rankPredictions"
            :disabled="!rankModel || rankingLoading"
            class="px-4 py-1.5 rounded-lg bg-gradient-to-r from-amber-500 to-fuchsia-500 hover:from-amber-600 hover:to-fuchsia-600 text-sm font-bold text-white transition disabled:opacity-50"
          >
            {{ rankingLoading ? 'AI 评审中...' : '开始排序' }}
          </button>
          <button
            v-if="ranking"
            @click="resetRanking"
            class="px-3 py-1.5 rounded-lg bg-white/10 hover:bg-white/20 text-slate-300 text-sm transition"
          >
            重置
          </button>
          <span class="text-xs text-slate-400">让 AI 评审所有候选组合并按推荐度排序</span>
        </div>
      </div>

      <!-- 排序结果 -->
      <div v-if="ranking" class="mb-6">
        <div class="text-sm text-slate-200 mb-3 flex items-center gap-2">
          <span class="font-semibold">🤖 AI 推荐排序</span>
          <span class="px-2 py-0.5 rounded-full bg-fuchsia-500/20 text-fuchsia-300 text-[10px] font-bold">{{ ranking.model }}</span>
        </div>
        <div class="space-y-2">
          <div
            v-for="(r, i) in sortedPredictions"
            :key="i"
            class="p-3 rounded-lg border transition"
            :class="i === 0 ? 'border-amber-400/50 bg-amber-500/10' : i === 1 ? 'border-slate-300/30 bg-slate-300/5' : i === 2 ? 'border-amber-700/40 bg-amber-700/5' : 'border-white/10 bg-white/5'"
          >
            <div class="flex items-center gap-2 mb-2">
              <span
                class="w-7 h-7 flex items-center justify-center rounded-full font-bold text-xs shrink-0"
                :class="i === 0 ? 'bg-amber-400 text-slate-900' : i === 1 ? 'bg-slate-300 text-slate-900' : i === 2 ? 'bg-amber-700 text-white' : 'bg-white/10 text-slate-300'"
              >
                #{{ i + 1 }}
              </span>
              <span
                class="px-2 py-0.5 rounded-full text-[10px] font-bold tabular-nums"
                :class="r.score >= 80 ? 'bg-emerald-500/20 text-emerald-300' : r.score >= 60 ? 'bg-amber-500/20 text-amber-300' : 'bg-slate-500/20 text-slate-400'"
              >
                {{ r.score }}分
              </span>
              <span class="px-2 py-0.5 rounded-full bg-fuchsia-500/20 text-fuchsia-300 text-[10px]">{{ r.source_model }}</span>
              <div class="flex-1" />
              <button
                @click="adoptRanked(r)"
                :disabled="rankAdoptingIdx === i"
                class="px-3 py-1 rounded-lg bg-violet-500/30 hover:bg-violet-500/50 text-violet-200 text-xs font-bold transition disabled:opacity-50"
              >
                {{ rankAdoptingIdx === i ? '采纳中...' : '采纳' }}
              </button>
            </div>
            <BallDisplay :red-balls="r.red_balls" :blue-balls="r.blue_balls" />
            <div v-if="r.comment" class="text-xs text-slate-400 mt-2 leading-relaxed">{{ r.comment }}</div>
          </div>
        </div>
      </div>

      <div class="space-y-6 mb-6">
        <div
          v-for="(group, gIdx) in result.results"
          :key="gIdx"
          class="rounded-xl border border-white/10 overflow-hidden"
        >
          <!-- 模型分组头 -->
          <div class="flex items-center justify-between px-4 py-2 bg-white/5 border-b border-white/10">
            <div class="flex items-center gap-2">
              <button
                v-if="!group.error && group.predictions.length"
                @click="toggleCollapse(group.model)"
                class="text-slate-400 hover:text-slate-200 transition shrink-0"
                :title="isCollapsed(group.model) ? '展开' : '收起'"
              >
                <svg class="w-4 h-4 transition-transform" :class="isCollapsed(group.model) ? '-rotate-90' : ''" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <polyline points="6 9 12 15 18 9"/>
                </svg>
              </button>
              <span class="text-sm font-bold text-slate-200">{{ group.model }}</span>
              <span
                v-if="group.error"
                class="px-2 py-0.5 rounded-full bg-red-500/20 text-red-300 text-[10px]"
              >失败</span>
              <span
                v-else-if="group.meta?.used_llm"
                class="px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 text-[10px]"
              >LLM</span>
              <span
                v-else
                class="px-2 py-0.5 rounded-full bg-slate-500/20 text-slate-400 text-[10px]"
              >启发式</span>
            </div>
            <div class="flex items-center gap-2">
              <span v-if="!group.error" class="text-xs text-slate-500">{{ group.predictions.length }} 注</span>
              <label
                v-if="!group.error && group.predictions.length"
                class="flex items-center gap-1 text-xs text-slate-400 cursor-pointer select-none"
              >
                <input
                  type="checkbox"
                  :checked="isGroupAllSelected(group)"
                  @change="toggleGroupAll(group, $event.target.checked)"
                  class="w-3.5 h-3.5 accent-violet-500"
                />
                全选
              </label>
              <button
                v-if="!group.error && group.predictions.length"
                @click="adoptGroupSelected(group)"
                :disabled="groupAdopting.has(group.model) || !groupSelectedCount(group)"
                class="px-2 py-1 rounded-lg bg-violet-500/30 hover:bg-violet-500/50 text-violet-200 text-xs font-bold transition disabled:opacity-50"
              >
                {{ groupAdopting.has(group.model) ? '采纳中' : `采纳选中(${groupSelectedCount(group)})` }}
              </button>
            </div>
          </div>

          <!-- 错误提示 -->
          <div v-if="group.error" class="p-4 text-sm text-red-300">
            {{ group.error }}
          </div>

          <!-- 分析说明 -->
          <div
            v-else-if="group.analysis"
            v-show="!isCollapsed(group.model)"
            class="p-3 text-xs text-slate-400 leading-relaxed border-b border-white/5"
          >
            {{ group.analysis }}
          </div>

          <!-- 预测号码列表 -->
          <div v-if="!group.error && group.predictions.length" v-show="!isCollapsed(group.model)" class="p-3 space-y-2">
            <div
              v-for="(pred, idx) in group.predictions"
              :key="idx"
              class="p-3 rounded-lg bg-violet-500/5 border border-violet-400/15"
            >
              <PredictionCard
                :pred="pred"
                :idx="idx"
                :adopting="isAdopting(group.model, idx)"
                :model="group.model"
                @toggle="pred.selected = !pred.selected"
                @adopt="adopt(pred, group.model)"
              />
            </div>
          </div>
        </div>
      </div>
    </template>

    <!-- ========== 历史预测记录 ========== -->
    <div class="mt-8">
      <div class="flex items-center justify-between mb-2">
        <div class="text-sm text-slate-400">历史预测记录</div>
        <div class="flex items-center gap-2">
          <span class="text-xs text-slate-500">筛选模型:</span>
          <USelect
            v-model="historyModelFilter"
            :options="historyModelOptions"
            placeholder="全部模型"
            align-right
            @change="loadHistory"
            class="w-[160px]"
          />
        </div>
      </div>
      <div class="overflow-x-auto rounded-xl border border-white/10">
        <table class="w-full text-sm">
          <thead>
            <tr class="bg-white/5 text-slate-300">
              <th class="px-3 py-2 text-left font-semibold">基于期号</th>
              <th class="px-3 py-2 text-left font-semibold">模型</th>
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
                <span
                  v-if="r.llm_model"
                  class="px-2 py-0.5 rounded-full bg-fuchsia-500/20 text-fuchsia-300 text-[10px]"
                >{{ r.llm_model }}</span>
                <span v-else class="text-slate-600 text-xs">-</span>
              </td>
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
        <div v-if="!history.length" class="text-center py-8 text-slate-500 text-sm">
          暂无历史预测记录
        </div>
      </div>
    </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { api } from '../api.js'
import { useToast } from '../composables/useToast.js'
import BallDisplay from './BallDisplay.vue'
import ModelSelector from './ModelSelector.vue'
import PredictionCard from './PredictionCard.vue'
import BatchBar from './BatchBar.vue'
import USelect from './USelect.vue'

const toast = useToast()
const count = ref(1)
const generating = ref(false)
const result = ref(null)
const history = ref([])
const historyModels = ref([])
const historyModelFilter = ref('')
const selectedModels = ref([])

// 单模型批量采纳状态
const adoptingIdx = ref(-1)
const batchAdopting = ref(false)
const adoptProgress = ref(0)

// 多模型采纳状态：key=`${model}:${idx}`
const adoptingKeys = ref(new Set())

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

function isAdopting(model, idx) {
  return adoptingKeys.value.has(`${model}:${idx}`)
}

async function adopt(pred, model) {
  const idx = result.value?.predictions?.indexOf(pred) ?? -1
  const key = `${model}:${idx}`
  // 单模型用 adoptingIdx，多模型用 adoptingKeys
  const isMulti = result.value?.multi
  if (isMulti) {
    adoptingKeys.value.add(key)
  } else {
    adoptingIdx.value = idx
  }
  try {
    const r = await api.adoptBet(
      pred.red_balls,
      pred.blue_balls,
      '',
      'ai_predict',
      pred.reason || '',
      model,
    )
    toast.success(r.message)
    window.dispatchEvent(new CustomEvent('lottery-data-updated'))
  } catch (e) {
    toast.error('采纳失败: ' + e.message)
  } finally {
    if (isMulti) {
      adoptingKeys.value.delete(key)
    } else {
      adoptingIdx.value = -1
    }
  }
}

async function adoptSelected() {
  const picks = (result.value?.predictions || []).filter(p => p.selected)
  if (!picks.length) return
  batchAdopting.value = true
  adoptProgress.value = 0
  let success = 0
  let failed = 0
  const model = result.value?.meta?.model || ''
  for (const pred of picks) {
    try {
      await api.adoptBet(
        pred.red_balls,
        pred.blue_balls,
        '',
        'ai_predict',
        pred.reason || '',
        model,
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
    window.dispatchEvent(new CustomEvent('lottery-data-updated'))
  } else if (failed > 0) {
    toast.error(`采纳全部失败 (${failed} 注)`)
  }
}

// 多模型分组：折叠 + 全选 + 批量采纳
const collapsedGroups = ref(new Set())
const groupAdopting = ref(new Set())

function isCollapsed(model) {
  return collapsedGroups.value.has(model)
}
function toggleCollapse(model) {
  const s = new Set(collapsedGroups.value)
  if (s.has(model)) s.delete(model)
  else s.add(model)
  collapsedGroups.value = s
}
function isGroupAllSelected(group) {
  return group.predictions?.length > 0 && group.predictions.every(p => p.selected)
}
function toggleGroupAll(group, checked) {
  group.predictions.forEach(p => { p.selected = checked })
}
function groupSelectedCount(group) {
  return (group.predictions || []).filter(p => p.selected).length
}
async function adoptGroupSelected(group) {
  const picks = (group.predictions || []).filter(p => p.selected)
  if (!picks.length) return
  const s = new Set(groupAdopting.value)
  s.add(group.model)
  groupAdopting.value = s
  let success = 0
  let failed = 0
  for (const pred of picks) {
    try {
      await api.adoptBet(pred.red_balls, pred.blue_balls, '', 'ai_predict', pred.reason || '', group.model)
      success++
    } catch (e) {
      failed++
      console.error('采纳失败:', e.message)
    }
  }
  const s2 = new Set(groupAdopting.value)
  s2.delete(group.model)
  groupAdopting.value = s2
  if (success > 0) {
    toast.success(`成功采纳 ${success} 注` + (failed > 0 ? `（${failed} 注失败）` : ''))
    window.dispatchEvent(new CustomEvent('lottery-data-updated'))
  } else if (failed > 0) {
    toast.error(`采纳全部失败 (${failed} 注)`)
  }
}

function resetPredictions() {
  result.value = null
  ranking.value = null
  collapsedGroups.value = new Set()
}

// 二次预测排序（评审）
const rankModel = ref('')
const ranking = ref(null)
const rankingLoading = ref(false)
const rankAdoptingIdx = ref(-1)

const rankModels = computed(() => {
  if (!result.value?.multi) return []
  const set = new Set()
  result.value.results.forEach(g => set.add(g.model))
  selectedModels.value.forEach(m => set.add(m))
  return [...set]
})

const rankModelOptions = computed(() => rankModels.value.map(m => ({ value: m, label: m })))
const historyModelOptions = computed(() => [
  { value: '', label: '全部模型' },
  ...historyModels.value.map(m => ({ value: m, label: m })),
])

// 把所有多模型预测的号码组合汇总成扁平列表（带 source_model）
const flatPredictions = computed(() => {
  if (!result.value?.multi) return []
  const out = []
  result.value.results.forEach(g => {
    if (!g.error) {
      g.predictions.forEach(p => {
        out.push({ ...p, source_model: g.model })
      })
    }
  })
  return out
})

const sortedPredictions = computed(() => {
  if (!ranking.value || !flatPredictions.value.length) return []
  return ranking.value.ranking.map(r => {
    const p = flatPredictions.value[r.index] || {}
    return { ...p, score: r.score, comment: r.comment }
  })
})

async function rankPredictions() {
  if (!rankModel.value || !flatPredictions.value.length) return
  rankingLoading.value = true
  ranking.value = null
  try {
    const r = await api.predictRank(flatPredictions.value, rankModel.value)
    if (r.error) {
      toast.error(r.error)
      return
    }
    ranking.value = r
    toast.success(`AI 排序完成（共 ${r.ranking.length} 组）`)
  } catch (e) {
    toast.error('排序失败: ' + e.message)
  } finally {
    rankingLoading.value = false
  }
}

function resetRanking() {
  ranking.value = null
}

async function adoptRanked(r) {
  const idx = sortedPredictions.value.indexOf(r)
  rankAdoptingIdx.value = idx
  try {
    const res = await api.adoptBet(
      r.red_balls,
      r.blue_balls,
      '',
      'ai_predict',
      r.comment || r.reason || '',
      r.source_model,
    )
    toast.success(res.message)
    window.dispatchEvent(new CustomEvent('lottery-data-updated'))
  } catch (e) {
    toast.error('采纳失败: ' + e.message)
  } finally {
    rankAdoptingIdx.value = -1
  }
}

async function generate() {
  generating.value = true
  result.value = null
  ranking.value = null
  try {
    const r = await api.predict(count.value, selectedModels.value)
    if (r.error) {
      toast.error(r.error)
      return
    }
    if (r.multi) {
      // 多模型结果
      result.value = r
      // 给每个 group 的 predictions 加 selected 属性，默认全选
      r.results.forEach(g => {
        if (!g.error && g.predictions) {
          g.predictions.forEach(p => { p.selected = true })
        }
      })
      collapsedGroups.value = new Set()
      const ok = r.results.filter(x => !x.error).length
      const fail = r.results.filter(x => x.error).length
      toast.success(`多模型预测完成: ${ok} 成功${fail ? ` · ${fail} 失败` : ''}`)
    } else {
      // 单模型结果
      result.value = r
      // 为每注添加 selected 属性，默认全选
      result.value.predictions.forEach(p => { p.selected = true })
      toast.success('预测生成成功')
    }
    loadHistory()
  } catch (e) {
    toast.error('预测失败: ' + e.message)
  } finally {
    generating.value = false
  }
}

async function loadHistory() {
  try {
    const [data, modelsData] = await Promise.all([
      api.getPredictions(30, historyModelFilter.value),
      api.getPredictionModels(),
    ])
    history.value = data
    historyModels.value = modelsData.models || []
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

function formatMoney(n) {
  if (n >= 1_0000_0000) return (n / 1_0000_0000).toFixed(2) + '亿'
  if (n >= 1_0000) return (n / 1_0000).toFixed(1) + '万'
  return n + '元'
}

onMounted(loadHistory)
</script>
