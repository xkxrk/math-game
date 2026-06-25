<template>
  <div>
    <!-- 子标签 -->
    <div class="flex flex-wrap gap-2 mb-4">
      <button
        v-for="sub in subTabs"
        :key="sub.id"
        @click="subActive = sub.id"
        :class="[
          'px-4 py-2 rounded-lg text-sm font-bold transition',
          subActive === sub.id
            ? 'bg-violet-500 text-white shadow'
            : 'bg-white/10 text-slate-300 hover:bg-white/20',
        ]"
      >
        {{ sub.name }}
      </button>
    </div>

    <!-- ========== 1. 号码组合诊断器 ========== -->
    <div v-show="subActive === 'doctor'">
      <p class="text-xs text-slate-500 mb-4">
        输入一组号码，立即得到形态体检报告：和值/奇偶/大小/跨度/AC值/区间分布等指标 + 历史分位对比 + 综合评分。
        <span class="text-amber-400/70">提示：评分仅反映该组合形态在历史中是否典型，不能预测中奖。</span>
      </p>

      <div class="p-4 rounded-xl bg-white/5 border border-white/10 mb-4">
        <div class="mb-3">
          <label class="block text-xs text-slate-400 mb-2">前区(5个，01-35)</label>
          <div class="flex flex-wrap gap-2">
            <input
              v-for="(_, i) in docReds"
              :key="'dr' + i"
              v-model="docReds[i]"
              type="text"
              maxlength="2"
              placeholder="00"
              class="w-12 h-12 text-center text-lg font-bold bg-red-500/20 border border-red-400/30 rounded-lg text-red-200 outline-none focus:border-red-400"
            />
          </div>
        </div>
        <div class="mb-3">
          <label class="block text-xs text-slate-400 mb-2">后区(2个，01-12)</label>
          <div class="flex gap-2">
            <input
              v-for="(_, i) in docBlues"
              :key="'db' + i"
              v-model="docBlues[i]"
              type="text"
              maxlength="2"
              placeholder="00"
              class="w-12 h-12 text-center text-lg font-bold bg-blue-500/20 border border-blue-400/30 rounded-lg text-blue-200 outline-none focus:border-blue-400"
            />
          </div>
        </div>
        <div class="flex gap-2 flex-wrap">
          <button
            @click="runDoctor"
            :disabled="docLoading"
            class="px-5 py-2 rounded-lg bg-violet-500 hover:bg-violet-600 text-white text-sm font-bold transition disabled:opacity-50"
          >
            {{ docLoading ? '诊断中...' : '开始诊断' }}
          </button>
          <button
            @click="fillRandomForDoc"
            class="px-4 py-2 rounded-lg bg-white/10 hover:bg-white/20 text-slate-300 text-sm transition"
          >
            随机填入
          </button>
          <button
            v-if="latestDraw"
            @click="fillLatest"
            class="px-4 py-2 rounded-lg bg-white/10 hover:bg-white/20 text-slate-300 text-sm transition"
          >
            填入上期开奖
          </button>
        </div>
      </div>

      <!-- 诊断结果 -->
      <div v-if="docResult" class="space-y-4">
        <!-- 评分大卡 -->
        <div
          class="p-5 rounded-xl border text-center"
          :class="scoreCardClass"
        >
          <div class="text-xs text-slate-400 mb-1">综合评分</div>
          <div class="text-5xl font-bold mb-1">{{ docResult.score }}</div>
          <div class="text-sm text-slate-300">{{ scoreDesc }}</div>
        </div>

        <!-- 形态指标 -->
        <div class="p-4 rounded-xl bg-white/5 border border-white/10">
          <div class="text-xs text-slate-400 mb-3">形态指标</div>
          <div class="grid grid-cols-2 md:grid-cols-4 gap-3">
            <div class="text-center">
              <div class="text-xs text-slate-500">和值</div>
              <div class="text-lg font-bold text-slate-200 tabular-nums">{{ docResult.stats.sum }}</div>
              <div class="text-[10px] text-slate-500">分位 {{ docResult.history_compare.sum_percentile }}%</div>
            </div>
            <div class="text-center">
              <div class="text-xs text-slate-500">奇偶比</div>
              <div class="text-lg font-bold text-slate-200">{{ docResult.stats.odd_even }}</div>
              <div class="text-[10px] text-slate-500">奇:偶</div>
            </div>
            <div class="text-center">
              <div class="text-xs text-slate-500">大小比</div>
              <div class="text-lg font-bold text-slate-200">{{ docResult.stats.big_small }}</div>
              <div class="text-[10px] text-slate-500">大:小(≥18:≤17)</div>
            </div>
            <div class="text-center">
              <div class="text-xs text-slate-500">跨度</div>
              <div class="text-lg font-bold text-slate-200 tabular-nums">{{ docResult.stats.span }}</div>
              <div class="text-[10px] text-slate-500">分位 {{ docResult.history_compare.span_percentile }}%</div>
            </div>
            <div class="text-center">
              <div class="text-xs text-slate-500">AC值</div>
              <div class="text-lg font-bold text-slate-200 tabular-nums">{{ docResult.stats.ac_value }}</div>
              <div class="text-[10px] text-slate-500">差值种类数</div>
            </div>
            <div class="text-center">
              <div class="text-xs text-slate-500">连号</div>
              <div class="text-lg font-bold text-slate-200 tabular-nums">{{ docResult.stats.consecutive }}</div>
              <div class="text-[10px] text-slate-500">对</div>
            </div>
            <div class="text-center">
              <div class="text-xs text-slate-500">同尾组</div>
              <div class="text-lg font-bold text-slate-200 tabular-nums">{{ docResult.stats.tail_groups }}</div>
              <div class="text-[10px] text-slate-500">组</div>
            </div>
            <div class="text-center">
              <div class="text-xs text-slate-500">重号</div>
              <div class="text-lg font-bold text-slate-200 tabular-nums">{{ docResult.stats.repeat_count ?? '-' }}</div>
              <div class="text-[10px] text-slate-500">与上期</div>
            </div>
          </div>
          <!-- 区间分布 -->
          <div class="mt-3 pt-3 border-t border-white/10">
            <div class="text-xs text-slate-500 mb-2">三区分布（1-12 / 13-23 / 24-35）</div>
            <div class="flex gap-1 h-6 rounded overflow-hidden">
              <div
                v-for="(z, i) in docResult.stats.zones"
                :key="i"
                :style="{ width: (z / 5 * 100) + '%', backgroundColor: zoneColors[i] }"
                class="flex items-center justify-center text-xs font-bold text-white"
              >
                {{ z }}
              </div>
            </div>
          </div>
        </div>

        <!-- 历史对比 -->
        <div class="p-4 rounded-xl bg-white/5 border border-white/10">
          <div class="text-xs text-slate-400 mb-2">历史规律对比</div>
          <div class="space-y-1 text-sm">
            <div class="text-slate-300">{{ docResult.history_compare.odd_even_rate }}</div>
            <div class="text-slate-300">{{ docResult.history_compare.big_small_rate }}</div>
            <div class="text-slate-300">
              历史完全相同的组合出现次数: <span class="font-bold text-amber-300">{{ docResult.history_compare.similar_count }}</span>
            </div>
          </div>
        </div>

        <!-- 所选号码遗漏值 -->
        <div class="p-4 rounded-xl bg-white/5 border border-white/10">
          <div class="text-xs text-slate-400 mb-2">所选号码当前遗漏值</div>
          <div class="flex flex-wrap gap-2">
            <div
              v-for="(miss, num) in docResult.miss_of_picks"
              :key="num"
              class="px-3 py-1 rounded-full text-xs"
              :class="miss >= 30 ? 'bg-amber-500/20 text-amber-300' : miss >= 15 ? 'bg-yellow-500/20 text-yellow-300' : 'bg-slate-500/20 text-slate-300'"
            >
              {{ num }} <span class="font-bold">{{ miss }}期</span>
            </div>
          </div>
        </div>

        <!-- 诊断提示 -->
        <div class="p-4 rounded-xl bg-amber-500/5 border border-amber-400/20">
          <div class="text-xs text-amber-300 mb-2">诊断提示</div>
          <ul class="space-y-1 text-sm text-slate-300">
            <li v-for="(tip, i) in docResult.tips" :key="i" class="flex gap-2">
              <span class="text-amber-400">•</span>
              <span>{{ tip }}</span>
            </li>
          </ul>
        </div>
      </div>
    </div>

    <!-- ========== 2. 遗漏值排行 ========== -->
    <div v-show="subActive === 'miss'">
      <div class="flex items-center gap-3 mb-4">
        <select
          v-model="missType"
          @change="loadMiss"
          class="bg-white/10 border border-white/20 rounded-lg px-3 py-2 text-sm text-slate-100 outline-none"
        >
          <option value="red" class="bg-slate-800">前区(1-35)</option>
          <option value="blue" class="bg-slate-800">后区(1-12)</option>
        </select>
        <span class="text-xs text-slate-500">遗漏值=距上次出现已隔几期（基于最近200期）。颜色越深表示遗漏越久。</span>
      </div>

      <div v-if="missData" class="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-5 lg:grid-cols-7 gap-3">
        <div
          v-for="item in missData.ranking"
          :key="item.num"
          class="p-3 rounded-xl border text-center transition"
          :class="missCardClass(item.miss)"
        >
          <!-- 号码球（大显眼） -->
          <div class="flex justify-center mb-2">
            <span
              class="inline-flex items-center justify-center w-10 h-10 rounded-full text-white text-base font-bold shadow-lg"
              :class="missType === 'red'
                ? 'bg-gradient-to-br from-red-500 to-red-600'
                : 'bg-gradient-to-br from-blue-500 to-blue-600'"
            >
              {{ item.num }}
            </span>
          </div>
          <!-- 遗漏期数 -->
          <div class="text-2xl font-extrabold tabular-nums" :class="missTextColor(item.miss)">{{ item.miss }}</div>
          <div class="text-[10px] text-slate-500 mt-0.5">期未出</div>
        </div>
      </div>
    </div>

    <!-- ========== 3. 和值分布 ========== -->
    <div v-show="subActive === 'sum'">
      <p class="text-xs text-slate-500 mb-4">前区5个号码之和的历史分布（最近200期）。</p>
      <div v-if="sumData" class="space-y-4">
        <!-- 汇总 -->
        <div class="grid grid-cols-3 gap-3">
          <div class="p-3 rounded-xl bg-white/5 border border-white/10 text-center">
            <div class="text-xs text-slate-400">最小</div>
            <div class="text-xl font-bold text-slate-200 tabular-nums">{{ sumData.min }}</div>
          </div>
          <div class="p-3 rounded-xl bg-white/5 border border-white/10 text-center">
            <div class="text-xs text-slate-400">平均</div>
            <div class="text-xl font-bold text-amber-300 tabular-nums">{{ sumData.avg }}</div>
          </div>
          <div class="p-3 rounded-xl bg-white/5 border border-white/10 text-center">
            <div class="text-xs text-slate-400">最大</div>
            <div class="text-xl font-bold text-slate-200 tabular-nums">{{ sumData.max }}</div>
          </div>
        </div>
        <!-- 分桶条形图 -->
        <div class="p-4 rounded-xl bg-white/5 border border-white/10">
          <div class="text-xs text-slate-400 mb-3">分桶统计</div>
          <div class="space-y-2">
            <div v-for="b in sumData.buckets" :key="b.range" class="flex items-center gap-3">
              <div class="w-16 text-xs text-slate-400 tabular-nums">{{ b.range }}</div>
              <div class="flex-1 bg-white/5 rounded overflow-hidden h-6 relative">
                <div
                  class="h-full bg-gradient-to-r from-violet-500 to-fuchsia-500 flex items-center justify-end pr-2"
                  :style="{ width: Math.max(b.rate * 100 * 2, 5) + '%' }"
                >
                  <span class="text-[10px] text-white font-bold">{{ b.count }}</span>
                </div>
              </div>
              <div class="w-12 text-xs text-slate-400 text-right tabular-nums">{{ (b.rate * 100).toFixed(1) }}%</div>
            </div>
          </div>
        </div>
        <!-- 最近30期和值折线 -->
        <div class="p-4 rounded-xl bg-white/5 border border-white/10">
          <div class="text-xs text-slate-400 mb-2">最近30期和值走势（新→旧）</div>
          <SumLineChart :values="sumData.recent" />
        </div>
      </div>
    </div>

    <!-- ========== 4. 奇偶/大小比 ========== -->
    <div v-show="subActive === 'ratio'">
      <div class="flex items-center gap-3 mb-4">
        <select
          v-model="ratioType"
          @change="loadRatio"
          class="bg-white/10 border border-white/20 rounded-lg px-3 py-2 text-sm text-slate-100 outline-none"
        >
          <option value="odd_even" class="bg-slate-800">奇偶比</option>
          <option value="big_small" class="bg-slate-800">大小比</option>
        </select>
        <span class="text-xs text-slate-500">{{ ratioType === 'odd_even' ? '5个号码中奇数:偶数' : '5个号码中大号(≥18):小号(≤17)' }}</span>
      </div>
      <div v-if="ratioData" class="space-y-3">
        <div
          v-for="item in ratioData.distribution"
          :key="item.ratio"
          class="flex items-center gap-3"
        >
          <div class="w-16 text-sm font-bold text-slate-200">{{ item.ratio }}</div>
          <div class="flex-1 bg-white/5 rounded overflow-hidden h-7 relative">
            <div
              class="h-full bg-gradient-to-r from-emerald-500 to-cyan-500 flex items-center justify-end pr-2"
              :style="{ width: Math.max(item.count / ratioData.total_draws * 100 * 2, 5) + '%' }"
            >
              <span class="text-[10px] text-white font-bold">{{ item.count }}</span>
            </div>
          </div>
          <div class="w-16 text-xs text-slate-400 text-right tabular-nums">
            {{ (item.count / ratioData.total_draws * 100).toFixed(1) }}%
          </div>
        </div>
      </div>
    </div>

    <!-- ========== 5. 奖池趋势 ========== -->
    <div v-show="subActive === 'pool'">
      <p class="text-xs text-slate-500 mb-4">历史奖池金额趋势（最近100期，单位：亿元）。</p>
      <div v-if="poolData" class="space-y-3">
        <div class="grid grid-cols-3 gap-3">
          <div class="p-3 rounded-xl bg-white/5 border border-white/10 text-center">
            <div class="text-xs text-slate-400">最低</div>
            <div class="text-lg font-bold text-slate-200 tabular-nums">{{ poolMinLabel }}</div>
          </div>
          <div class="p-3 rounded-xl bg-white/5 border border-white/10 text-center">
            <div class="text-xs text-slate-400">平均</div>
            <div class="text-lg font-bold text-amber-300 tabular-nums">{{ poolAvgLabel }}</div>
          </div>
          <div class="p-3 rounded-xl bg-white/5 border border-white/10 text-center">
            <div class="text-xs text-slate-400">最高</div>
            <div class="text-lg font-bold text-slate-200 tabular-nums">{{ poolMaxLabel }}</div>
          </div>
        </div>
        <div class="p-4 rounded-xl bg-white/5 border border-white/10">
          <div class="text-xs text-slate-400 mb-2">奖池趋势折线（新→旧）</div>
          <PoolLineChart :values="poolChartValues" />
        </div>
        <div class="text-[10px] text-slate-500">
          注：奖池≥8亿时新规则触发固定奖金上浮（三等5,000→6,666元，四等300→380元等）。
        </div>
      </div>
    </div>

    <!-- ========== 6. 号码频率统计（含命中率汇总） ========== -->
    <div v-show="subActive === 'frequency'">
      <div class="flex items-center justify-between mb-4">
        <h3 class="text-lg font-bold text-slate-100">号码频率统计</h3>
        <button
          @click="loadAll"
          :disabled="freqLoading"
          class="px-3 py-1.5 rounded-lg bg-white/10 hover:bg-white/20 text-sm text-slate-100 transition disabled:opacity-50"
        >
          {{ freqLoading ? '加载中...' : '刷新' }}
        </button>
      </div>

      <!-- 命中率汇总 -->
      <div v-if="hitSummary" class="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6">
        <div class="p-3 rounded-xl bg-white/5 border border-white/10 text-center">
          <div class="text-2xl font-extrabold text-slate-100">{{ hitSummary.total }}</div>
          <div class="text-xs text-slate-400 mt-1">已评估预测</div>
        </div>
        <div class="p-3 rounded-xl bg-white/5 border border-white/10 text-center">
          <div class="text-2xl font-extrabold text-red-400">{{ hitSummary.avg_red }}</div>
          <div class="text-xs text-slate-400 mt-1">平均前区命中</div>
        </div>
        <div class="p-3 rounded-xl bg-white/5 border border-white/10 text-center">
          <div class="text-2xl font-extrabold text-blue-400">{{ hitSummary.avg_blue }}</div>
          <div class="text-xs text-slate-400 mt-1">平均后区命中</div>
        </div>
        <div class="p-3 rounded-xl bg-white/5 border border-white/10 text-center">
          <div class="text-2xl font-extrabold text-emerald-400">{{ hitSummary.best }}</div>
          <div class="text-xs text-slate-400 mt-1">最佳命中</div>
        </div>
      </div>

      <!-- 前区频率 + 遗漏值 -->
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div class="p-4 rounded-xl bg-white/5 border border-white/10">
          <div class="text-sm font-semibold text-red-400 mb-3">前区号码频率（含遗漏值，基于最近200期）</div>
          <div class="space-y-2 max-h-[600px] overflow-y-auto pr-3">
            <div
              v-for="item in redFreq"
              :key="item.num"
              class="flex items-center gap-2"
            >
              <span
                class="w-8 h-8 flex-shrink-0 inline-flex items-center justify-center rounded-full text-white text-xs font-bold shadow"
                :class="item.miss >= 30 ? 'bg-gradient-to-br from-amber-500 to-amber-600' : 'bg-gradient-to-br from-red-500 to-red-600'"
              >
                {{ item.num }}
              </span>
              <div class="flex-1 h-5 bg-white/5 rounded-full overflow-hidden">
                <div
                  class="h-full bg-gradient-to-r from-red-500 to-red-400 rounded-full transition-all"
                  :style="{ width: freqWidth(item.count, 'red') + '%' }"
                ></div>
              </div>
              <span class="w-10 text-right text-xs text-slate-300 tabular-nums">{{ item.count }}次</span>
              <span
                class="w-12 text-right text-[11px] tabular-nums font-semibold"
                :class="item.miss >= 30 ? 'text-amber-400' : item.miss >= 15 ? 'text-yellow-400' : 'text-slate-500'"
              >
                遗{{ item.miss }}
              </span>
            </div>
          </div>
        </div>

        <div class="p-4 rounded-xl bg-white/5 border border-white/10">
          <div class="text-sm font-semibold text-blue-400 mb-3">后区号码频率（含遗漏值）</div>
          <div class="space-y-2">
            <div
              v-for="item in blueFreq"
              :key="item.num"
              class="flex items-center gap-2"
            >
              <span
                class="w-8 h-8 flex-shrink-0 inline-flex items-center justify-center rounded-full text-white text-xs font-bold shadow"
                :class="item.miss >= 30 ? 'bg-gradient-to-br from-amber-500 to-amber-600' : 'bg-gradient-to-br from-blue-500 to-blue-600'"
              >
                {{ item.num }}
              </span>
              <div class="flex-1 h-5 bg-white/5 rounded-full overflow-hidden">
                <div
                  class="h-full bg-gradient-to-r from-blue-500 to-blue-400 rounded-full transition-all"
                  :style="{ width: freqWidth(item.count, 'blue') + '%' }"
                ></div>
              </div>
              <span class="w-10 text-right text-xs text-slate-300 tabular-nums">{{ item.count }}次</span>
              <span
                class="w-12 text-right text-[11px] tabular-nums font-semibold"
                :class="item.miss >= 30 ? 'text-amber-400' : item.miss >= 15 ? 'text-yellow-400' : 'text-slate-500'"
              >
                遗{{ item.miss }}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- ========== 7. 期望值计算器 ========== -->
    <div v-show="subActive === 'expected-value'">
      <p class="text-xs text-slate-500 mb-4">
        一等奖单注期望值 = 当前奖池 / 总组合数(21,425,712)。期望值 &gt; 2 元成本视为正期望。
      </p>
      <div v-if="evData" class="space-y-4">
        <!-- 当前奖池 + 期望值大卡 -->
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div class="p-5 rounded-xl bg-white/5 border border-white/10 text-center">
            <div class="text-xs text-slate-400 mb-2">当前奖池</div>
            <div class="text-4xl font-extrabold text-amber-300 tabular-nums">
              {{ (evData.current_pool / 1_0000_0000).toFixed(2) }}
              <span class="text-base text-slate-400">亿</span>
            </div>
            <div class="text-xs text-slate-500 mt-1 tabular-nums">≈ {{ evData.current_pool.toLocaleString() }} 元</div>
          </div>
          <div
            class="p-5 rounded-xl border text-center"
            :class="evData.is_positive_ev ? 'bg-emerald-500/10 border-emerald-400/30' : 'bg-red-500/10 border-red-400/30'"
          >
            <div class="text-xs text-slate-400 mb-2">一等奖单注期望值</div>
            <div
              class="text-4xl font-extrabold tabular-nums"
              :class="evData.is_positive_ev ? 'text-emerald-400' : 'text-red-400'"
            >
              {{ evData.first_prize_ev }}
              <span class="text-base text-slate-400">元</span>
            </div>
            <div class="text-xs mt-1" :class="evData.is_positive_ev ? 'text-emerald-300' : 'text-red-300'">
              {{ evData.is_positive_ev ? '正期望（> 2元成本）' : '负期望（< 2元成本）' }}
            </div>
          </div>
        </div>

        <!-- 期望值进度条 -->
        <div class="p-4 rounded-xl bg-white/5 border border-white/10">
          <div class="flex justify-between text-xs text-slate-400 mb-2">
            <span>期望值 vs 2元成本</span>
            <span class="tabular-nums">{{ evData.first_prize_ev }} / 2 元</span>
          </div>
          <div class="relative h-6 bg-white/5 rounded-full overflow-hidden">
            <!-- 2元成本刻度线 -->
            <div
              class="absolute top-0 bottom-0 w-0.5 bg-amber-400 z-10"
              :style="{ left: evBarCostPos + '%' }"
            ></div>
            <div
              class="h-full rounded-full transition-all"
              :class="evData.is_positive_ev
                ? 'bg-gradient-to-r from-emerald-500 to-emerald-400'
                : 'bg-gradient-to-r from-red-500 to-red-400'"
              :style="{ width: evBarWidth + '%' }"
            ></div>
          </div>
          <div class="flex justify-between text-[10px] text-slate-500 mt-1 tabular-nums">
            <span>0</span>
            <span>2元(成本)</span>
            <span>{{ evBarMax }}元</span>
          </div>
        </div>

        <!-- 历史奖池分位图 -->
        <div class="p-4 rounded-xl bg-white/5 border border-white/10">
          <div class="flex justify-between items-center mb-3">
            <div class="text-xs text-slate-400">历史奖池分位（基于最近100期）</div>
            <div class="text-xs text-slate-300 tabular-nums">
              当前处于 <span class="font-bold text-amber-300">{{ evData.pool_history_percentile }}%</span> 分位
            </div>
          </div>
          <!-- min/p25/median/p75/max 五个刻度 -->
          <div class="relative h-12 bg-white/5 rounded-lg overflow-hidden">
            <!-- 当前值位置高亮 -->
            <div
              class="absolute top-0 bottom-0 w-1 bg-amber-400 z-20 shadow-lg"
              :style="{ left: `calc(${evData.pool_history_percentile}% - 2px)` }"
            ></div>
            <div
              class="absolute -top-0.5 text-[9px] text-amber-300 z-20 -translate-x-1/2 whitespace-nowrap"
              :style="{ left: evData.pool_history_percentile + '%' }"
            >
              当前
            </div>
            <!-- 5 刻度 -->
            <div class="absolute inset-0 flex">
              <div class="flex-1 border-r border-white/10"></div>
              <div class="flex-1 border-r border-white/10"></div>
              <div class="flex-1 border-r border-white/10"></div>
              <div class="flex-1 border-r border-white/10"></div>
              <div class="flex-1"></div>
            </div>
          </div>
          <div class="grid grid-cols-5 gap-2 mt-2 text-center">
            <div>
              <div class="text-[10px] text-slate-500">min</div>
              <div class="text-xs font-bold text-slate-300 tabular-nums">{{ (evData.pool_history_stats.min / 1_0000_0000).toFixed(2) }}亿</div>
            </div>
            <div>
              <div class="text-[10px] text-slate-500">p25</div>
              <div class="text-xs font-bold text-slate-300 tabular-nums">{{ (evData.pool_history_stats.p25 / 1_0000_0000).toFixed(2) }}亿</div>
            </div>
            <div>
              <div class="text-[10px] text-slate-500">中位</div>
              <div class="text-xs font-bold text-slate-300 tabular-nums">{{ (evData.pool_history_stats.median / 1_0000_0000).toFixed(2) }}亿</div>
            </div>
            <div>
              <div class="text-[10px] text-slate-500">p75</div>
              <div class="text-xs font-bold text-slate-300 tabular-nums">{{ (evData.pool_history_stats.p75 / 1_0000_0000).toFixed(2) }}亿</div>
            </div>
            <div>
              <div class="text-[10px] text-slate-500">max</div>
              <div class="text-xs font-bold text-slate-300 tabular-nums">{{ (evData.pool_history_stats.max / 1_0000_0000).toFixed(2) }}亿</div>
            </div>
          </div>
        </div>

        <!-- 总组合数 + 推荐 -->
        <div class="p-4 rounded-xl bg-violet-500/5 border border-violet-400/20">
          <div class="text-xs text-violet-300 mb-2">投资建议</div>
          <div class="text-sm text-slate-200">{{ evData.recommendation }}</div>
          <div class="text-[10px] text-slate-500 mt-2 tabular-nums">
            总组合数 C(35,5) × C(12,2) = {{ evData.total_combinations.toLocaleString() }}
          </div>
        </div>
      </div>
      <div v-else class="text-center text-slate-500 py-8">加载中...</div>
    </div>

    <!-- ========== 8. 策略对比 ========== -->
    <div v-show="subActive === 'strategy-compare'">
      <p class="text-xs text-slate-500 mb-4">
        4 种固定策略在最近 {{ strategyData?.periods || 100 }} 期上的命中率/ROI 对比。每策略每期固定购买 1 注。
      </p>
      <div v-if="strategyData" class="space-y-4">
        <!-- 4 个策略卡片 -->
        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          <div
            v-for="(s, idx) in strategyData.strategies"
            :key="s.name"
            class="p-4 rounded-xl bg-white/5 border border-white/10"
          >
            <div class="text-sm font-bold text-slate-100 mb-2">{{ s.name }}</div>
            <!-- 号码 -->
            <div class="mb-3">
              <div class="flex flex-wrap gap-1 mb-1">
                <span
                  v-for="n in s.red_balls"
                  :key="'sr' + n + idx"
                  class="inline-flex items-center justify-center w-7 h-7 rounded-full text-white text-xs font-bold bg-gradient-to-br from-red-500 to-red-600"
                >{{ n }}</span>
                <span class="mx-1 text-slate-600">|</span>
                <span
                  v-for="n in s.blue_balls"
                  :key="'sb' + n + idx"
                  class="inline-flex items-center justify-center w-7 h-7 rounded-full text-white text-xs font-bold bg-gradient-to-br from-blue-500 to-blue-600"
                >{{ n }}</span>
              </div>
            </div>
            <!-- 指标 -->
            <div class="space-y-1 text-xs">
              <div class="flex justify-between">
                <span class="text-slate-400">总花费</span>
                <span class="text-slate-200 tabular-nums">{{ s.total_cost }}元</span>
              </div>
              <div class="flex justify-between">
                <span class="text-slate-400">总中奖</span>
                <span class="text-amber-300 tabular-nums">{{ s.total_winnings }}元</span>
              </div>
              <div class="flex justify-between">
                <span class="text-slate-400">净收益</span>
                <span
                  class="font-bold tabular-nums"
                  :class="s.net_profit >= 0 ? 'text-emerald-400' : 'text-red-400'"
                >
                  {{ s.net_profit >= 0 ? '+' : '' }}{{ s.net_profit }}元
                </span>
              </div>
              <div class="flex justify-between">
                <span class="text-slate-400">中奖率</span>
                <span class="text-slate-200 tabular-nums">{{ s.win_rate }}%</span>
              </div>
              <div class="flex justify-between">
                <span class="text-slate-400">ROI</span>
                <span
                  class="font-bold tabular-nums"
                  :class="s.roi >= 0 ? 'text-emerald-400' : 'text-red-400'"
                >
                  {{ s.roi >= 0 ? '+' : '' }}{{ s.roi }}%
                </span>
              </div>
            </div>
            <!-- 中奖等级分布 -->
            <div v-if="Object.keys(s.level_stats).length" class="mt-3 pt-3 border-t border-white/10">
              <div class="text-[10px] text-slate-500 mb-1">中奖等级</div>
              <div class="flex flex-wrap gap-1">
                <span
                  v-for="(cnt, lv) in s.level_stats"
                  :key="lv"
                  class="px-2 py-0.5 rounded text-[10px] bg-slate-500/20 text-slate-300"
                >{{ lv }} ×{{ cnt }}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- 累计 ROI 曲线对比（用 div 柱状图替代 ECharts） -->
        <div class="p-4 rounded-xl bg-white/5 border border-white/10">
          <div class="text-xs text-slate-400 mb-3">最终净收益对比</div>
          <div class="space-y-2">
            <div
              v-for="s in strategyData.strategies"
              :key="'bar' + s.name"
              class="flex items-center gap-3"
            >
              <div class="w-16 text-xs text-slate-300">{{ s.name }}</div>
              <div class="flex-1 relative h-6 bg-white/5 rounded overflow-hidden">
                <div
                  v-if="s.net_profit >= 0"
                  class="absolute left-1/2 top-0 bottom-0 bg-gradient-to-r from-emerald-500 to-emerald-400"
                  :style="{ width: strategyBarWidth(s.net_profit) + '%' }"
                ></div>
                <div
                  v-else
                  class="absolute right-1/2 top-0 bottom-0 bg-gradient-to-l from-red-500 to-red-400"
                  :style="{ width: strategyBarWidth(s.net_profit) + '%' }"
                ></div>
                <!-- 中线 -->
                <div class="absolute left-1/2 top-0 bottom-0 w-px bg-white/30"></div>
              </div>
              <div
                class="w-20 text-xs text-right font-bold tabular-nums"
                :class="s.net_profit >= 0 ? 'text-emerald-400' : 'text-red-400'"
              >
                {{ s.net_profit >= 0 ? '+' : '' }}{{ s.net_profit }}
              </div>
            </div>
          </div>
          <div class="text-[10px] text-slate-500 mt-2">注：以最终净收益绝对值的最大值为基准，向左为亏损，向右为盈利。</div>
        </div>
      </div>
      <div v-else class="text-center text-slate-500 py-8">加载中...</div>
    </div>

    <!-- ========== 9. 历史复盘 ========== -->
    <div v-show="subActive === 'review'">
      <p class="text-xs text-slate-500 mb-4">
        选择一期号先选号，再揭晓开奖结果，对比你的号码与实际开奖的命中情况与形态。
      </p>

      <!-- 期号选择 -->
      <div class="flex flex-wrap items-end gap-3 mb-4">
        <div>
          <label class="block text-xs text-slate-400 mb-1">选择期号</label>
          <select
            v-model="reviewIssue"
            @change="onReviewIssueChange"
            class="bg-white/10 border border-white/20 rounded-lg px-3 py-2 text-sm text-slate-100 outline-none min-w-[200px]"
          >
            <option value="" class="bg-slate-800">-- 请选择 --</option>
            <option v-for="i in reviewIssues" :key="i.issue" :value="i.issue" class="bg-slate-800">
              {{ i.issue }} ({{ i.date }})
            </option>
          </select>
        </div>
        <button
          v-if="reviewResult"
          @click="nextReview"
          class="px-4 py-2 rounded-lg bg-white/10 hover:bg-white/20 text-sm text-slate-100 transition"
        >
          下一期
        </button>
      </div>

      <div v-if="reviewIssue && !reviewResult">
        <!-- 选号区 -->
        <div class="p-4 rounded-xl bg-white/5 border border-white/10 mb-4">
          <div class="text-xs text-slate-400 mb-3">请先选号，再揭晓</div>
          <div class="mb-3">
            <label class="block text-xs text-slate-400 mb-2">前区(5个，01-35)</label>
            <div class="flex flex-wrap gap-2">
              <input
                v-for="(_, i) in reviewReds"
                :key="'rr' + i"
                v-model="reviewReds[i]"
                type="text"
                maxlength="2"
                placeholder="00"
                class="w-12 h-12 text-center text-lg font-bold bg-red-500/20 border border-red-400/30 rounded-lg text-red-200 outline-none focus:border-red-400"
              />
            </div>
          </div>
          <div class="mb-3">
            <label class="block text-xs text-slate-400 mb-2">后区(2个，01-12)</label>
            <div class="flex gap-2">
              <input
                v-for="(_, i) in reviewBlues"
                :key="'rb' + i"
                v-model="reviewBlues[i]"
                type="text"
                maxlength="2"
                placeholder="00"
                class="w-12 h-12 text-center text-lg font-bold bg-blue-500/20 border border-blue-400/30 rounded-lg text-blue-200 outline-none focus:border-blue-400"
              />
            </div>
          </div>
          <div class="flex gap-2 flex-wrap">
            <button
              @click="revealReview"
              :disabled="reviewLoading"
              class="px-5 py-2 rounded-lg bg-violet-500 hover:bg-violet-600 text-white text-sm font-bold transition disabled:opacity-50"
            >
              {{ reviewLoading ? '揭晓中...' : '揭晓' }}
            </button>
            <button
              @click="fillRandomReview"
              class="px-4 py-2 rounded-lg bg-white/10 hover:bg-white/20 text-slate-300 text-sm transition"
            >
              随机填入
            </button>
          </div>
        </div>
      </div>

      <!-- 复盘结果 -->
      <div v-if="reviewResult" class="space-y-4">
        <!-- 综合评分 -->
        <div
          class="p-5 rounded-xl border text-center"
          :class="reviewScoreCardClass"
        >
          <div class="text-xs text-slate-400 mb-1">综合评分</div>
          <div class="text-5xl font-bold mb-1">{{ reviewResult.score }}</div>
          <div class="text-sm text-slate-300">{{ reviewScoreDesc }}</div>
        </div>

        <!-- 双栏对比 -->
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <!-- 你的号码 -->
          <div class="p-4 rounded-xl bg-violet-500/5 border border-violet-400/20">
            <div class="text-xs text-violet-300 mb-2">你的号码</div>
            <BallDisplay :red-balls="reviewResult.your_stats.red_balls" :blue-balls="reviewResult.your_stats.blue_balls" />
            <div class="mt-3 grid grid-cols-2 gap-2 text-xs">
              <div><span class="text-slate-500">和值:</span> <span class="text-slate-200 tabular-nums">{{ reviewResult.your_stats.sum }}</span></div>
              <div><span class="text-slate-500">奇偶比:</span> <span class="text-slate-200">{{ reviewResult.your_stats.odd_even }}</span></div>
              <div><span class="text-slate-500">大小比:</span> <span class="text-slate-200">{{ reviewResult.your_stats.big_small }}</span></div>
              <div><span class="text-slate-500">跨度:</span> <span class="text-slate-200 tabular-nums">{{ reviewResult.your_stats.span }}</span></div>
            </div>
          </div>
          <!-- 实际开奖 -->
          <div class="p-4 rounded-xl bg-amber-500/5 border border-amber-400/20">
            <div class="text-xs text-amber-300 mb-2">
              实际开奖 · {{ reviewIssue }}
            </div>
            <BallDisplay :red-balls="reviewResult.actual_red_balls" :blue-balls="reviewResult.actual_blue_balls" />
            <div class="mt-3 grid grid-cols-2 gap-2 text-xs">
              <div><span class="text-slate-500">和值:</span> <span class="text-slate-200 tabular-nums">{{ reviewResult.actual_stats.sum }}</span></div>
              <div><span class="text-slate-500">奇偶比:</span> <span class="text-slate-200">{{ reviewResult.actual_stats.odd_even }}</span></div>
              <div><span class="text-slate-500">大小比:</span> <span class="text-slate-200">{{ reviewResult.actual_stats.big_small }}</span></div>
              <div><span class="text-slate-500">跨度:</span> <span class="text-slate-200 tabular-nums">{{ reviewResult.actual_stats.span }}</span></div>
            </div>
          </div>
        </div>

        <!-- 命中信息 -->
        <div class="p-4 rounded-xl bg-white/5 border border-white/10">
          <div class="text-xs text-slate-400 mb-3">命中详情</div>
          <div class="grid grid-cols-2 sm:grid-cols-4 gap-3 text-center">
            <div>
              <div class="text-xs text-slate-500">前区命中</div>
              <div class="text-xl font-bold text-red-400 tabular-nums">{{ reviewResult.red_hits }} / 5</div>
            </div>
            <div>
              <div class="text-xs text-slate-500">后区命中</div>
              <div class="text-xl font-bold text-blue-400 tabular-nums">{{ reviewResult.blue_hits }} / 2</div>
            </div>
            <div>
              <div class="text-xs text-slate-500">奖金等级</div>
              <div class="text-xl font-bold text-slate-200">{{ reviewResult.desc }}</div>
            </div>
            <div>
              <div class="text-xs text-slate-500">奖金</div>
              <div class="text-xl font-bold text-amber-300 tabular-nums">{{ reviewResult.amount }}元</div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- ========== 10. 策略沙盒 ========== -->
    <div v-show="subActive === 'sandbox'">
      <p class="text-xs text-slate-500 mb-4">
        自定义形态规则，生成多注合格号码并模拟在最近100期上购买，观察命中率与收益。
      </p>

      <!-- 规则配置 -->
      <div class="p-4 rounded-xl bg-white/5 border border-white/10 mb-4">
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <!-- 和值范围 -->
          <div>
            <label class="block text-xs text-slate-400 mb-2">和值范围</label>
            <div class="flex items-center gap-2">
              <input
                v-model.number="sandboxRules.sum_min"
                type="number"
                class="w-24 bg-white/10 border border-white/20 rounded-lg px-3 py-2 text-sm text-slate-100 outline-none"
                placeholder="min"
              />
              <span class="text-slate-500">~</span>
              <input
                v-model.number="sandboxRules.sum_max"
                type="number"
                class="w-24 bg-white/10 border border-white/20 rounded-lg px-3 py-2 text-sm text-slate-100 outline-none"
                placeholder="max"
              />
            </div>
          </div>
          <!-- 跨度范围 -->
          <div>
            <label class="block text-xs text-slate-400 mb-2">跨度范围</label>
            <div class="flex items-center gap-2">
              <input
                v-model.number="sandboxRules.span_min"
                type="number"
                class="w-24 bg-white/10 border border-white/20 rounded-lg px-3 py-2 text-sm text-slate-100 outline-none"
                placeholder="min"
              />
              <span class="text-slate-500">~</span>
              <input
                v-model.number="sandboxRules.span_max"
                type="number"
                class="w-24 bg-white/10 border border-white/20 rounded-lg px-3 py-2 text-sm text-slate-100 outline-none"
                placeholder="max"
              />
            </div>
          </div>
          <!-- 奇偶比 -->
          <div>
            <label class="block text-xs text-slate-400 mb-2">奇偶比（多选）</label>
            <div class="flex flex-wrap gap-1">
              <button
                v-for="r in ratioOptions"
                :key="'oe' + r"
                @click="toggleArray(sandboxRules.odd_even, r)"
                :class="[
                  'px-2 py-1 rounded text-xs transition',
                  sandboxRules.odd_even.includes(r)
                    ? 'bg-violet-500 text-white'
                    : 'bg-white/10 text-slate-300 hover:bg-white/20',
                ]"
              >{{ r }}</button>
            </div>
          </div>
          <!-- 大小比 -->
          <div>
            <label class="block text-xs text-slate-400 mb-2">大小比（多选）</label>
            <div class="flex flex-wrap gap-1">
              <button
                v-for="r in ratioOptions"
                :key="'bs' + r"
                @click="toggleArray(sandboxRules.big_small, r)"
                :class="[
                  'px-2 py-1 rounded text-xs transition',
                  sandboxRules.big_small.includes(r)
                    ? 'bg-violet-500 text-white'
                    : 'bg-white/10 text-slate-300 hover:bg-white/20',
                ]"
              >{{ r }}</button>
            </div>
          </div>
          <!-- 连号开关 -->
          <div>
            <label class="block text-xs text-slate-400 mb-2">是否允许连号</label>
            <button
              @click="sandboxRules.consecutive = !sandboxRules.consecutive"
              :class="[
                'px-4 py-2 rounded-lg text-sm font-bold transition',
                sandboxRules.consecutive
                  ? 'bg-emerald-500 text-white'
                  : 'bg-white/10 text-slate-300 hover:bg-white/20',
              ]"
            >
              {{ sandboxRules.consecutive ? '允许' : '禁止' }}
            </button>
          </div>
          <!-- 生成注数 -->
          <div>
            <label class="block text-xs text-slate-400 mb-2">生成注数</label>
            <div class="flex gap-1">
              <button
                v-for="n in [1, 3, 5, 10]"
                :key="n"
                @click="sandboxRules.combo_count = n"
                :class="[
                  'px-3 py-1.5 rounded text-xs transition',
                  sandboxRules.combo_count === n
                    ? 'bg-violet-500 text-white'
                    : 'bg-white/10 text-slate-300 hover:bg-white/20',
                ]"
              >{{ n }} 注</button>
            </div>
          </div>
        </div>
        <div class="mt-4">
          <button
            @click="runSandbox"
            :disabled="sandboxLoading"
            class="px-5 py-2 rounded-lg bg-violet-500 hover:bg-violet-600 text-white text-sm font-bold transition disabled:opacity-50"
          >
            {{ sandboxLoading ? '模拟中...' : '开始模拟' }}
          </button>
        </div>
      </div>

      <!-- 沙盒结果 -->
      <div v-if="sandboxResult" class="space-y-4">
        <!-- 模拟汇总 -->
        <div class="grid grid-cols-2 sm:grid-cols-5 gap-3">
          <div class="p-3 rounded-xl bg-white/5 border border-white/10 text-center">
            <div class="text-xs text-slate-400">总花费</div>
            <div class="text-lg font-bold text-slate-200 tabular-nums">{{ sandboxResult.simulation.total_cost }}元</div>
          </div>
          <div class="p-3 rounded-xl bg-white/5 border border-white/10 text-center">
            <div class="text-xs text-slate-400">总中奖</div>
            <div class="text-lg font-bold text-amber-300 tabular-nums">{{ sandboxResult.simulation.total_winnings }}元</div>
          </div>
          <div class="p-3 rounded-xl bg-white/5 border border-white/10 text-center">
            <div class="text-xs text-slate-400">净收益</div>
            <div
              class="text-lg font-bold tabular-nums"
              :class="sandboxResult.simulation.net_profit >= 0 ? 'text-emerald-400' : 'text-red-400'"
            >
              {{ sandboxResult.simulation.net_profit >= 0 ? '+' : '' }}{{ sandboxResult.simulation.net_profit }}元
            </div>
          </div>
          <div class="p-3 rounded-xl bg-white/5 border border-white/10 text-center">
            <div class="text-xs text-slate-400">中奖率</div>
            <div class="text-lg font-bold text-slate-200 tabular-nums">{{ sandboxResult.simulation.win_rate }}%</div>
          </div>
          <div class="p-3 rounded-xl bg-white/5 border border-white/10 text-center">
            <div class="text-xs text-slate-400">ROI</div>
            <div
              class="text-lg font-bold tabular-nums"
              :class="sandboxResult.simulation.roi >= 0 ? 'text-emerald-400' : 'text-red-400'"
            >
              {{ sandboxResult.simulation.roi >= 0 ? '+' : '' }}{{ sandboxResult.simulation.roi }}%
            </div>
          </div>
        </div>

        <!-- 中奖等级分布 -->
        <div v-if="Object.keys(sandboxResult.simulation.level_stats).length" class="p-4 rounded-xl bg-white/5 border border-white/10">
          <div class="text-xs text-slate-400 mb-2">中奖等级分布</div>
          <div class="flex flex-wrap gap-2">
            <span
              v-for="(cnt, lv) in sandboxResult.simulation.level_stats"
              :key="lv"
              class="px-3 py-1 rounded-full text-xs bg-slate-500/20 text-slate-300"
            >{{ lv }} ×{{ cnt }}</span>
          </div>
        </div>

        <!-- 生成的号码列表 -->
        <div class="p-4 rounded-xl bg-white/5 border border-white/10">
          <div class="text-xs text-slate-400 mb-3">生成的号码（共 {{ sandboxResult.generated_combos.length }} 注）</div>
          <div class="space-y-3">
            <div
              v-for="(combo, idx) in sandboxResult.generated_combos"
              :key="'combo' + idx"
              class="p-3 rounded-lg bg-white/5 border border-white/10"
            >
              <div class="flex items-center justify-between mb-2">
                <span class="text-xs text-slate-400">第 {{ idx + 1 }} 注</span>
              </div>
              <BallDisplay :red-balls="combo.red_balls" :blue-balls="combo.blue_balls" />
              <div class="mt-2 grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs">
                <div><span class="text-slate-500">和值:</span> <span class="text-slate-200 tabular-nums">{{ combo.stats.sum }}</span></div>
                <div><span class="text-slate-500">奇偶比:</span> <span class="text-slate-200">{{ combo.stats.odd_even }}</span></div>
                <div><span class="text-slate-500">大小比:</span> <span class="text-slate-200">{{ combo.stats.big_small }}</span></div>
                <div><span class="text-slate-500">跨度:</span> <span class="text-slate-200 tabular-nums">{{ combo.stats.span }}</span></div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- ========== 11. 实时预警 ========== -->
    <div v-show="subActive === 'alerts'">
      <!-- 顶部状态条 -->
      <div class="flex items-center justify-between mb-4 flex-wrap gap-2">
        <div class="flex items-center gap-2">
          <span
            class="w-2.5 h-2.5 rounded-full"
            :class="alertsConnected ? 'bg-emerald-400 animate-pulse' : 'bg-red-400'"
          ></span>
          <span class="text-sm" :class="alertsConnected ? 'text-emerald-300' : 'text-red-300'">
            {{ alertsConnected ? '实时连接中' : '连接断开，5秒后重连' }}
          </span>
        </div>
        <div v-if="alertsData" class="text-xs text-slate-500 tabular-nums">
          更新 {{ alertsTimeLabel }} · 期号 {{ alertsData.latest_issue ?? '-' }}
        </div>
      </div>

      <div v-if="alertsData" class="space-y-4">
        <!-- 奖池状态卡片 -->
        <div class="p-4 rounded-xl bg-white/5 border border-white/10">
          <div class="flex items-center justify-between mb-3">
            <div class="text-xs text-slate-400">奖池状态</div>
            <span
              class="px-2 py-0.5 rounded-full text-[10px] font-bold"
              :class="alertsData.pool_status.is_high_pool
                ? 'bg-emerald-500/20 text-emerald-300'
                : 'bg-amber-500/20 text-amber-300'"
            >
              {{ alertsData.pool_status.is_high_pool ? '已达8亿阈值' : '未达8亿阈值' }}
            </span>
          </div>
          <div class="flex items-end gap-2 mb-3">
            <div class="text-3xl font-extrabold tabular-nums" :class="poolAmountColor">
              {{ poolAmountLabel }}
            </div>
            <div class="text-xs text-slate-500 mb-1">当前奖池金额</div>
          </div>
          <!-- 阈值进度条 -->
          <div class="mb-1 flex items-center justify-between text-[10px] text-slate-500">
            <span>0</span>
            <span>阈值 8亿</span>
          </div>
          <div class="h-2.5 bg-white/5 rounded-full overflow-hidden">
            <div
              class="h-full rounded-full transition-all"
              :class="alertsData.pool_status.is_high_pool
                ? 'bg-gradient-to-r from-emerald-500 to-emerald-400'
                : 'bg-gradient-to-r from-amber-500 to-amber-400'"
              :style="{ width: poolProgressPercent + '%' }"
            ></div>
          </div>
          <div class="text-xs text-slate-400 mt-2">{{ alertsData.pool_status.message }}</div>
        </div>

        <!-- 高遗漏号码 -->
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <!-- 前区高遗漏 -->
          <div class="p-4 rounded-xl bg-white/5 border border-white/10">
            <div class="flex items-center justify-between mb-3">
              <div class="text-sm font-semibold text-red-400">前区高遗漏 (≥15期)</div>
              <span class="text-xs text-slate-500">{{ alertsData.high_miss_red.length }} 个</span>
            </div>
            <div v-if="alertsData.high_miss_red.length" class="grid grid-cols-2 sm:grid-cols-3 gap-3">
              <div
                v-for="item in alertsData.high_miss_red"
                :key="'ar' + item.number"
                class="flex items-center gap-2 p-2 rounded-lg bg-white/5"
              >
                <span
                  class="w-9 h-9 flex-shrink-0 inline-flex items-center justify-center rounded-full text-red-200 text-sm font-bold bg-red-500/30"
                >
                  {{ padAlertNum(item.number) }}
                </span>
                <div>
                  <div class="text-xl font-extrabold tabular-nums leading-none" :class="missTextColor(item.miss)">
                    {{ item.miss }}
                  </div>
                  <div class="text-[10px] text-slate-500">期未出</div>
                </div>
              </div>
            </div>
            <div v-else class="text-xs text-slate-500 py-4 text-center">暂无高遗漏号码</div>
          </div>

          <!-- 后区高遗漏 -->
          <div class="p-4 rounded-xl bg-white/5 border border-white/10">
            <div class="flex items-center justify-between mb-3">
              <div class="text-sm font-semibold text-blue-400">后区高遗漏 (≥10期)</div>
              <span class="text-xs text-slate-500">{{ alertsData.high_miss_blue.length }} 个</span>
            </div>
            <div v-if="alertsData.high_miss_blue.length" class="grid grid-cols-2 sm:grid-cols-3 gap-3">
              <div
                v-for="item in alertsData.high_miss_blue"
                :key="'ab' + item.number"
                class="flex items-center gap-2 p-2 rounded-lg bg-white/5"
              >
                <span
                  class="w-9 h-9 flex-shrink-0 inline-flex items-center justify-center rounded-full text-blue-200 text-sm font-bold bg-blue-500/30"
                >
                  {{ padAlertNum(item.number) }}
                </span>
                <div>
                  <div class="text-xl font-extrabold tabular-nums leading-none" :class="missTextColor(item.miss)">
                    {{ item.miss }}
                  </div>
                  <div class="text-[10px] text-slate-500">期未出</div>
                </div>
              </div>
            </div>
            <div v-else class="text-xs text-slate-500 py-4 text-center">暂无高遗漏号码</div>
          </div>
        </div>
      </div>

      <div v-else-if="!alertsConnected" class="text-center text-slate-500 text-sm py-8">
        正在连接预警服务...
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch, onUnmounted } from 'vue'
import { api } from '../api.js'
import { useToast } from '../composables/useToast.js'
import BallDisplay from './BallDisplay.vue'
import SumLineChart from './charts/SumLineChart.vue'
import PoolLineChart from './charts/PoolLineChart.vue'

const toast = useToast()
const subActive = ref('doctor')

const subTabs = [
  { id: 'doctor', name: '组合诊断' },
  { id: 'miss', name: '遗漏值' },
  { id: 'sum', name: '和值分布' },
  { id: 'ratio', name: '奇偶大小' },
  { id: 'pool', name: '奖池趋势' },
  { id: 'frequency', name: '频率统计' },
  { id: 'expected-value', name: '期望值' },
  { id: 'strategy-compare', name: '策略对比' },
  { id: 'review', name: '历史复盘' },
  { id: 'sandbox', name: '策略沙盒' },
  { id: 'alerts', name: '实时预警' },
]

// ---------- 组合诊断器 ----------
const docReds = ref(['', '', '', '', ''])
const docBlues = ref(['', ''])
const docLoading = ref(false)
const docResult = ref(null)
const latestDraw = ref(null)

const zoneColors = ['#ef4444', '#f59e0b', '#3b82f6']

const scoreCardClass = computed(() => {
  const s = docResult.value?.score ?? 0
  if (s >= 80) return 'bg-emerald-500/10 border-emerald-400/30'
  if (s >= 60) return 'bg-yellow-500/10 border-yellow-400/30'
  return 'bg-red-500/10 border-red-400/30'
})

const scoreDesc = computed(() => {
  const s = docResult.value?.score ?? 0
  if (s >= 80) return '形态典型，落入历史常见区间'
  if (s >= 60) return '形态尚可，存在个别极端指标'
  return '形态偏极端，建议调整'
})

function fillRandomForDoc() {
  const reds = new Set()
  while (reds.size < 5) reds.add(Math.floor(Math.random() * 35) + 1)
  const blues = new Set()
  while (blues.size < 2) blues.add(Math.floor(Math.random() * 12) + 1)
  docReds.value = [...reds].sort((a, b) => a - b).map(n => String(n).padStart(2, '0'))
  docBlues.value = [...blues].sort((a, b) => a - b).map(n => String(n).padStart(2, '0'))
}

function fillLatest() {
  if (!latestDraw.value) return
  docReds.value = [...latestDraw.value.red_balls]
  docBlues.value = [...latestDraw.value.blue_balls]
}

async function runDoctor() {
  const reds = docReds.value.filter(x => x !== '')
  const blues = docBlues.value.filter(x => x !== '')
  if (reds.length !== 5 || blues.length !== 2) {
    toast.error('请填入 5 个前区号码和 2 个后区号码')
    return
  }
  // 校验范围
  const redNums = reds.map(Number)
  const blueNums = blues.map(Number)
  if (redNums.some(n => n < 1 || n > 35)) {
    toast.error('前区号码必须在 01-35 之间')
    return
  }
  if (blueNums.some(n => n < 1 || n > 12)) {
    toast.error('后区号码必须在 01-12 之间')
    return
  }
  if (new Set(redNums).size !== 5) {
    toast.error('前区号码不能重复')
    return
  }
  if (new Set(blueNums).size !== 2) {
    toast.error('后区号码不能重复')
    return
  }
  docLoading.value = true
  try {
    docResult.value = await api.diagnoseCombo(
      reds.map(n => String(n).padStart(2, '0')),
      blues.map(n => String(n).padStart(2, '0')),
    )
    toast.success('诊断完成')
  } catch (e) {
    toast.error('诊断失败: ' + e.message)
  } finally {
    docLoading.value = false
  }
}

// ---------- 遗漏值 ----------
const missType = ref('red')
const missData = ref(null)

async function loadMiss() {
  try {
    missData.value = await api.getMiss(missType.value, 200)
  } catch (e) {
    toast.error('加载遗漏值失败: ' + e.message)
  }
}

function missCardClass(miss) {
  if (miss >= 30) return 'bg-amber-500/10 border-amber-400/30'
  if (miss >= 15) return 'bg-yellow-500/10 border-yellow-400/30'
  return 'bg-white/5 border-white/10'
}

function missTextColor(miss) {
  if (miss >= 30) return 'text-amber-300'
  if (miss >= 15) return 'text-yellow-300'
  return 'text-slate-200'
}

// ---------- 和值分布 ----------
const sumData = ref(null)

async function loadSum() {
  try {
    sumData.value = await api.getSumDistribution(200)
  } catch (e) {
    toast.error('加载和值分布失败: ' + e.message)
  }
}

// ---------- 奇偶/大小比 ----------
const ratioType = ref('odd_even')
const ratioData = ref(null)

async function loadRatio() {
  try {
    ratioData.value = await api.getRatio(ratioType.value, 200)
  } catch (e) {
    toast.error('加载分布失败: ' + e.message)
  }
}

// ---------- 奖池趋势 ----------
const poolData = ref(null)

const poolChartValues = computed(() => {
  if (!poolData.value) return []
  // trend 是升序(旧→新)，反转成新→旧
  return [...poolData.value.trend].reverse().map(t => t.pool)
})

const poolMinLabel = computed(() => {
  const vals = poolChartValues.value.filter(v => v != null)
  if (!vals.length) return '-'
  return (Math.min(...vals) / 1_0000_0000).toFixed(2) + '亿'
})

const poolMaxLabel = computed(() => {
  const vals = poolChartValues.value.filter(v => v != null)
  if (!vals.length) return '-'
  return (Math.max(...vals) / 1_0000_0000).toFixed(2) + '亿'
})

const poolAvgLabel = computed(() => {
  const vals = poolChartValues.value.filter(v => v != null)
  if (!vals.length) return '-'
  return (vals.reduce((a, b) => a + b, 0) / vals.length / 1_0000_0000).toFixed(2) + '亿'
})

async function loadPool() {
  try {
    poolData.value = await api.getPoolTrend(100)
  } catch (e) {
    toast.error('加载奖池趋势失败: ' + e.message)
  }
}

// ---------- 频率统计（合并原 StatsChart 功能）----------
const freqLoading = ref(false)
const redFreq = ref([])
const blueFreq = ref([])
const hitSummary = ref(null)

function freqWidth(count, type) {
  const arr = type === 'red' ? redFreq.value : blueFreq.value
  const max = arr[0]?.count || 1
  return Math.max(5, (count / max) * 100)
}

async function loadFrequency() {
  try {
    const [red, blue, stats] = await Promise.all([
      api.getFrequency('red', 200),
      api.getFrequency('blue', 200),
      api.getStats(100),
    ])
    redFreq.value = red.stats
    blueFreq.value = blue.stats
    hitSummary.value = stats.hit_summary
  } catch (e) {
    toast.error('加载频率统计失败: ' + e.message)
  }
}

async function loadAll() {
  freqLoading.value = true
  await loadFrequency()
  freqLoading.value = false
}

// ---------- 期望值计算器 ----------
const evData = ref(null)

// 进度条最大值（取期望值和 2 的最大值，再放大到合适刻度）
const evBarMax = computed(() => {
  const ev = evData.value?.first_prize_ev ?? 0
  // 至少 4 元刻度，避免期望值很小时进度条过满
  return Math.max(4, Math.ceil(Math.max(ev, 2) * 1.2))
})

const evBarWidth = computed(() => {
  const ev = evData.value?.first_prize_ev ?? 0
  return Math.min(100, (ev / evBarMax.value) * 100)
})

const evBarCostPos = computed(() => {
  // 2 元成本在进度条上的位置
  return Math.min(100, (2 / evBarMax.value) * 100)
})

async function loadExpectedValue() {
  try {
    evData.value = await api.getExpectedValue(100)
  } catch (e) {
    toast.error('加载期望值失败: ' + e.message)
  }
}

// ---------- 策略对比 ----------
const strategyData = ref(null)

async function loadStrategyCompare() {
  try {
    strategyData.value = await api.strategyCompare(100)
  } catch (e) {
    toast.error('加载策略对比失败: ' + e.message)
  }
}

// 柱状图宽度（按净收益绝对值的最大值归一化）
function strategyBarWidth(netProfit) {
  if (!strategyData.value?.strategies) return 0
  const maxAbs = Math.max(
    ...strategyData.value.strategies.map(s => Math.abs(s.net_profit)),
    1,
  )
  return Math.min(50, (Math.abs(netProfit) / maxAbs) * 50)
}

// ---------- 历史复盘 ----------
const reviewIssues = ref([])
const reviewIssue = ref('')
const reviewReds = ref(['', '', '', '', ''])
const reviewBlues = ref(['', ''])
const reviewLoading = ref(false)
const reviewResult = ref(null)

async function loadReviewIssues() {
  try {
    reviewIssues.value = await api.reviewIssues(50)
  } catch (e) {
    toast.error('加载期号列表失败: ' + e.message)
  }
}

function onReviewIssueChange() {
  // 切换期号时清空结果
  reviewResult.value = null
  reviewReds.value = ['', '', '', '', '']
  reviewBlues.value = ['', '']
}

function fillRandomReview() {
  const reds = new Set()
  while (reds.size < 5) reds.add(Math.floor(Math.random() * 35) + 1)
  const blues = new Set()
  while (blues.size < 2) blues.add(Math.floor(Math.random() * 12) + 1)
  reviewReds.value = [...reds].sort((a, b) => a - b).map(n => String(n).padStart(2, '0'))
  reviewBlues.value = [...blues].sort((a, b) => a - b).map(n => String(n).padStart(2, '0'))
}

async function revealReview() {
  if (!reviewIssue.value) {
    toast.error('请先选择期号')
    return
  }
  const reds = reviewReds.value.filter(x => x !== '')
  const blues = reviewBlues.value.filter(x => x !== '')
  if (reds.length !== 5 || blues.length !== 2) {
    toast.error('请填入 5 个前区号码和 2 个后区号码')
    return
  }
  const redNums = reds.map(Number)
  const blueNums = blues.map(Number)
  if (redNums.some(n => n < 1 || n > 35)) {
    toast.error('前区号码必须在 01-35 之间')
    return
  }
  if (blueNums.some(n => n < 1 || n > 12)) {
    toast.error('后区号码必须在 01-12 之间')
    return
  }
  if (new Set(redNums).size !== 5 || new Set(blueNums).size !== 2) {
    toast.error('号码不能重复')
    return
  }
  reviewLoading.value = true
  try {
    reviewResult.value = await api.reviewScore(
      reviewIssue.value,
      reds.map(n => String(n).padStart(2, '0')),
      blues.map(n => String(n).padStart(2, '0')),
    )
  } catch (e) {
    toast.error('揭晓失败: ' + e.message)
  } finally {
    reviewLoading.value = false
  }
}

function nextReview() {
  // 切到列表中的下一期
  const idx = reviewIssues.value.findIndex(i => i.issue === reviewIssue.value)
  if (idx > 0) {
    reviewIssue.value = reviewIssues.value[idx - 1].issue
  }
  onReviewIssueChange()
}

const reviewScoreCardClass = computed(() => {
  const s = reviewResult.value?.score ?? 0
  if (s >= 80) return 'bg-emerald-500/10 border-emerald-400/30'
  if (s >= 60) return 'bg-yellow-500/10 border-yellow-400/30'
  return 'bg-red-500/10 border-red-400/30'
})

const reviewScoreDesc = computed(() => {
  const s = reviewResult.value?.score ?? 0
  if (s >= 80) return '命中表现优秀，形态接近实际'
  if (s >= 60) return '命中表现尚可，形态有部分接近'
  return '命中表现一般，形态偏差较大'
})

// ---------- 策略沙盒 ----------
const ratioOptions = ['5:0', '4:1', '3:2', '2:3', '1:4', '0:5']
const sandboxRules = ref({
  sum_min: 80,
  sum_max: 130,
  odd_even: ['2:3', '3:2'],
  big_small: ['2:3', '3:2'],
  span_min: 15,
  span_max: 30,
  consecutive: false,
  combo_count: 5,
})
const sandboxLoading = ref(false)
const sandboxResult = ref(null)

function toggleArray(arr, val) {
  const idx = arr.indexOf(val)
  if (idx >= 0) {
    arr.splice(idx, 1)
  } else {
    arr.push(val)
  }
}

async function runSandbox() {
  sandboxLoading.value = true
  try {
    const rules = { ...sandboxRules.value }
    sandboxResult.value = await api.sandboxSimulate(rules, 100)
    if (sandboxResult.value.generated_combos.length === 0) {
      toast.info('未生成任何合格号码，请放宽规则')
    } else {
      toast.success(`生成 ${sandboxResult.value.generated_combos.length} 注号码`)
    }
  } catch (e) {
    toast.error('沙盒模拟失败: ' + e.message)
  } finally {
    sandboxLoading.value = false
  }
}

// ---------- 子标签切换懒加载 ----------
const loadedTabs = new Set()
watch(subActive, (newTab) => {
  if (loadedTabs.has(newTab)) return
  loadedTabs.add(newTab)
  if (newTab === 'expected-value') loadExpectedValue()
  else if (newTab === 'strategy-compare') loadStrategyCompare()
  else if (newTab === 'review') loadReviewIssues()
})

// ---------- 实时预警（SSE 订阅）----------
const alertsData = ref(null)
const alertsConnected = ref(false)
let alertsEventSource = null
let alertsReconnectTimer = null
const alertsNotified = new Set()

// 号码补零显示（后端返回整数，前端统一两位显示）
function padAlertNum(n) {
  return String(n).padStart(2, '0')
}

// 时间戳只取时间部分（形如 "2026-06-25T15:30:00" → "15:30:00"）
const alertsTimeLabel = computed(() => {
  const ts = alertsData.value?.timestamp
  if (!ts) return '-'
  return ts.split('T')[1] || ts
})

// 奖池金额（亿元）
const poolAmountLabel = computed(() => {
  const p = alertsData.value?.pool_status?.current_pool
  if (p == null) return '暂无数据'
  return (p / 1_0000_0000).toFixed(2) + ' 亿'
})

// 奖池金额颜色：达阈值用 emerald，否则用 amber
const poolAmountColor = computed(() => {
  return alertsData.value?.pool_status?.is_high_pool ? 'text-emerald-300' : 'text-amber-300'
})

// 奖池阈值进度条百分比（相对 8 亿阈值，封顶 100%）
const poolProgressPercent = computed(() => {
  const p = alertsData.value?.pool_status?.current_pool
  const threshold = alertsData.value?.pool_status?.threshold
  if (!p || !threshold) return 0
  return Math.min(100, Math.round((p / threshold) * 100))
})

function startAlerts() {
  // 先关闭旧连接，避免重复创建 EventSource
  stopAlerts()
  alertsEventSource = new EventSource('/api/sse/alerts')

  alertsEventSource.onopen = () => {
    alertsConnected.value = true
  }

  alertsEventSource.onmessage = (ev) => {
    alertsConnected.value = true
    try {
      const payload = JSON.parse(ev.data)
      alertsData.value = payload
      // 检查遗漏≥30期号码，弹 toast 提醒（每个号码仅提醒一次）
      const newHigh = []
      for (const item of payload.high_miss_red || []) {
        if (item.miss >= 30) {
          const key = 'r' + item.number
          if (!alertsNotified.has(key)) {
            newHigh.push(`前区${padAlertNum(item.number)}(${item.miss}期)`)
            alertsNotified.add(key)
          }
        }
      }
      for (const item of payload.high_miss_blue || []) {
        if (item.miss >= 30) {
          const key = 'b' + item.number
          if (!alertsNotified.has(key)) {
            newHigh.push(`后区${padAlertNum(item.number)}(${item.miss}期)`)
            alertsNotified.add(key)
          }
        }
      }
      if (newHigh.length) {
        toast.show(`遗漏预警：${newHigh.join('、')} 未出，建议关注`, 'error')
      }
    } catch (e) {
      // 解析失败忽略
    }
  }

  alertsEventSource.onerror = () => {
    alertsConnected.value = false
    // 关闭当前连接，5秒后手动重连
    if (alertsEventSource) {
      alertsEventSource.close()
      alertsEventSource = null
    }
    if (alertsReconnectTimer) clearTimeout(alertsReconnectTimer)
    alertsReconnectTimer = setTimeout(() => {
      // 仅当仍在预警标签页时才重连
      if (subActive.value === 'alerts') startAlerts()
    }, 5000)
  }
}

function stopAlerts() {
  if (alertsReconnectTimer) {
    clearTimeout(alertsReconnectTimer)
    alertsReconnectTimer = null
  }
  if (alertsEventSource) {
    alertsEventSource.close()
    alertsEventSource = null
  }
  alertsConnected.value = false
}

// 子标签切走时暂停订阅，切回时恢复
watch(subActive, (val) => {
  if (val === 'alerts') startAlerts()
  else stopAlerts()
})

// 组件卸载时关闭 EventSource 连接
onUnmounted(() => {
  stopAlerts()
})

// ---------- 初始化 ----------
onMounted(async () => {
  // 加载最新开奖（供"填入上期"按钮使用）
  try {
    latestDraw.value = await api.getLatest()
    const reds = latestDraw.value.red_balls.split(',').sort((a, b) => a - b)
    const blues = latestDraw.value.blue_balls.split(',').sort((a, b) => a - b)
    latestDraw.value.red_balls = reds
    latestDraw.value.blue_balls = blues
  } catch {}
  // 预加载各子标签数据
  loadMiss()
  loadSum()
  loadRatio()
  loadPool()
  loadFrequency()
})
</script>
