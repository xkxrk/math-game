<template>
  <div class="flex flex-col h-full min-h-0">
    <div class="flex items-center justify-between mb-4 shrink-0">
      <h3 class="text-lg font-bold text-slate-100">历史开奖</h3>
      <div class="flex items-center gap-2">
        <USelect
          v-model="limit"
          :options="[{value:30,label:'30 期'},{value:50,label:'50 期'},{value:100,label:'100 期'}]"
          @change="load"
          class="w-[100px]"
        />
        <button
          @click="refresh"
          :disabled="loading"
          class="px-3 py-1.5 rounded-lg bg-white/10 hover:bg-white/20 text-sm text-slate-100 transition disabled:opacity-50"
        >
          {{ loading ? '抓取中...' : '抓取最新' }}
        </button>
        <button
          @click="load"
          :disabled="loading"
          title="仅从本地数据库重新加载"
          class="px-3 py-1.5 rounded-lg bg-white/10 hover:bg-white/20 text-sm text-slate-100 transition disabled:opacity-50"
        >
          {{ loading ? '加载中...' : '刷新' }}
        </button>
      </div>
    </div>

    <div class="flex-1 min-h-0 overflow-auto rounded-xl border border-white/10">
      <table class="w-full text-sm whitespace-nowrap">
        <thead class="sticky top-0 z-10">
          <tr class="bg-slate-800/95 backdrop-blur text-slate-300">
            <th class="px-3 py-2.5 text-left font-semibold">期号</th>
            <th class="px-3 py-2.5 text-left font-semibold">开奖日</th>
            <th class="px-3 py-2.5 text-left font-semibold">前区</th>
            <th class="px-3 py-2.5 text-left font-semibold">后区</th>
            <th class="px-3 py-2.5 text-right font-semibold">奖池滚存</th>
            <th class="px-3 py-2.5 text-right font-semibold">一等奖</th>
            <th class="px-3 py-2.5 text-right font-semibold">二等奖</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="row in rows"
            :key="row.issue"
            class="border-t border-white/5 hover:bg-white/5 transition"
          >
            <td class="px-3 py-2.5 text-slate-300 tabular-nums">{{ row.issue }}</td>
            <td class="px-3 py-2.5 text-slate-400 tabular-nums">{{ formatDate(row.date) }}</td>
            <td class="px-3 py-2.5">
              <BallDisplay :red-balls="row.red_balls" :blue-balls="[]" />
            </td>
            <td class="px-3 py-2.5">
              <BallDisplay :red-balls="[]" :blue-balls="row.blue_balls" />
            </td>
            <td class="px-3 py-2.5 text-right text-amber-300 tabular-nums">
              {{ formatMoney(row.prize_pool) }}
            </td>
            <td class="px-3 py-2.5 text-right tabular-nums">
              <span class="text-slate-200">{{ row.first_prize_count || '-' }}注</span>
              <span class="text-slate-500 ml-1">{{ formatMoney(row.first_prize_amount) }}</span>
            </td>
            <td class="px-3 py-2.5 text-right tabular-nums">
              <span class="text-slate-200">{{ row.second_prize_count || '-' }}注</span>
              <span class="text-slate-500 ml-1">{{ formatMoney(row.second_prize_amount) }}</span>
            </td>
          </tr>
          <tr v-if="!rows.length && !loading">
            <td colspan="7" class="px-4 py-8 text-center text-slate-500">暂无数据，请先抓取</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { api } from '../api.js'
import { useToast } from '../composables/useToast.js'
import BallDisplay from './BallDisplay.vue'
import USelect from './USelect.vue'

const toast = useToast()
const rows = ref([])
const loading = ref(false)
const limit = ref(50)

async function load() {
  loading.value = true
  try {
    rows.value = await api.getHistory(limit.value)
  } catch (e) {
    toast.error('加载历史失败: ' + e.message)
  } finally {
    loading.value = false
  }
}

async function refresh() {
  loading.value = true
  try {
    // 先从 500.com 抓取最新数据
    const result = await api.triggerScrape(200)
    const added = result?.scrape?.added || result?.scrape?.inserted || 0
    const updated = result?.scrape?.updated || 0
    // 再从本地数据库重新加载
    rows.value = await api.getHistory(limit.value)
    if (added > 0) {
      toast.success(`已抓取最新数据，新增 ${added} 期${updated ? `，更新 ${updated} 期` : ''}`)
    } else if (updated > 0) {
      toast.success(`数据已是最新，更新 ${updated} 期`)
    } else {
      toast.success('数据已是最新')
    }
    // 通知其他组件数据已更新
    window.dispatchEvent(new CustomEvent('lottery-data-updated'))
  } catch (e) {
    toast.error('抓取失败: ' + e.message)
    // 失败时仍尝试加载本地数据
    try {
      rows.value = await api.getHistory(limit.value)
    } catch {}
  } finally {
    loading.value = false
  }
}

function formatDate(d) {
  if (!d) return '-'
  return d.slice(0, 10)
}

function formatMoney(s) {
  if (!s) return '-'
  // 去掉逗号，转为数字
  const n = parseFloat(String(s).replace(/,/g, ''))
  if (isNaN(n)) return s
  if (n >= 1e8) return (n / 1e8).toFixed(2) + '亿'
  if (n >= 1e4) return (n / 1e4).toFixed(1) + '万'
  return String(n)
}

onMounted(load)
defineExpose({ load })
</script>
