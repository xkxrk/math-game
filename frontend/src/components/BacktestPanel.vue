<template>
  <div class="h-full overflow-y-auto pr-1">
    <!-- 子标签 -->
    <div class="flex gap-2 mb-4">
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

    <!-- ========== 1. AI 预测回测 ========== -->
    <div v-show="subActive === 'backtest'">
      <div class="flex flex-wrap items-end gap-3 mb-4">
        <div>
          <label class="block text-xs text-slate-400 mb-1">选择回测期号</label>
          <USelect
            v-model="selectedIssue"
            :options="issueOptions"
            class="w-[200px]"
          />
        </div>
        <div>
          <label class="block text-xs text-slate-400 mb-1">加注数</label>
          <USelect
            v-model="backtestCount"
            :options="[{value:1,label:'1 注'},{value:3,label:'3 注'},{value:5,label:'5 注'},{value:10,label:'10 注'}]"
            class="w-[120px]"
          />
        </div>
        <div>
          <label class="block text-xs text-slate-400 mb-1">预测模型</label>
          <ModelSelector v-model="backtestModels" />
        </div>
        <button
          @click="runBacktest"
          :disabled="!selectedIssue || backtestLoading"
          class="px-5 py-2 rounded-lg bg-violet-500 hover:bg-violet-600 text-white text-sm font-bold transition disabled:opacity-50"
        >
          {{ backtestLoading ? 'AI 分析中...' : '开始回测' }}
        </button>
      </div>
      <p class="text-xs text-slate-500 mb-4">
        AI 将基于所选期号<strong class="text-slate-300">之前</strong>的历史数据生成 <strong class="text-violet-300">{{ backtestCount }} 注</strong>预测，再与该期实际开奖对比分别计算每注奖金。可选多模型对比。
      </p>

      <!-- 单模型回测结果 -->
      <div v-if="backtestResult && !backtestResult.multi" class="space-y-4">
        <!-- 实际开奖 -->
        <div class="p-4 rounded-xl bg-slate-500/10 border border-slate-400/20">
          <div class="flex items-center justify-between mb-2">
            <span class="text-xs text-slate-400">
              实际开奖 · {{ backtestResult.target_issue }} ({{ backtestResult.target_date }})
            </span>
            <span
              class="text-[10px] px-2 py-0.5 rounded-full"
              :class="backtestResult.used_llm ? 'bg-emerald-500/20 text-emerald-300' : 'bg-slate-500/20 text-slate-400'"
            >
              {{ backtestResult.used_llm ? backtestResult.llm_model : '启发式' }}
            </span>
          </div>
          <BallDisplay :red-balls="backtestResult.actual_red_balls" :blue-balls="backtestResult.actual_blue_balls" />
        </div>

        <!-- 每注预测 + 命中结果 -->
        <div class="space-y-3">
          <div
            v-for="(pred, idx) in backtestResult.predictions"
            :key="idx"
            class="p-4 rounded-xl border"
            :class="predPrizeCardClass(pred.prize.level)"
          >
            <div class="flex items-center justify-between mb-2">
              <span class="text-xs text-slate-400">
                第 {{ idx + 1 }} 注预测
                <span v-if="backtestResult.predictions.length > 1" class="ml-1 text-violet-300">· {{ pred.prize.desc }}</span>
              </span>
              <span
                v-if="pred.prize.amount > 0"
                class="text-lg font-bold text-amber-300"
              >
                {{ formatMoney(pred.prize.amount) }}
              </span>
            </div>
            <BallDisplay :red-balls="pred.red_balls" :blue-balls="pred.blue_balls" />
            <div class="mt-2 flex items-center justify-between text-xs">
              <span class="text-slate-400">
                前区命中 {{ pred.prize.red_hits }}/5 · 后区命中 {{ pred.prize.blue_hits }}/2
              </span>
              <span v-if="pred.prize.level > 0" class="font-bold" :class="predPrizeTextClass(pred.prize.level)">
                {{ pred.prize.desc }}
              </span>
              <span v-else class="text-slate-500">{{ pred.prize.desc }}</span>
            </div>
            <div v-if="pred.reason" class="mt-2 text-xs text-slate-400">
              <span class="text-violet-300">理由：</span>{{ pred.reason }}
            </div>
          </div>
        </div>

        <!-- 汇总卡片 -->
        <div class="grid grid-cols-3 gap-3">
          <div class="p-3 rounded-xl bg-white/5 border border-white/10 text-center">
            <div class="text-xs text-slate-400">总花费</div>
            <div class="text-lg font-bold text-slate-200">{{ backtestResult.total_cost }}元</div>
            <div class="text-[10px] text-slate-500">{{ backtestResult.bet_count }}注</div>
          </div>
          <div class="p-3 rounded-xl bg-white/5 border border-white/10 text-center">
            <div class="text-xs text-slate-400">总中奖</div>
            <div class="text-lg font-bold text-amber-300">{{ formatMoney(backtestResult.total_winnings) }}</div>
          </div>
          <div
            class="p-3 rounded-xl border text-center"
            :class="backtestResult.net_profit >= 0 ? 'bg-emerald-500/10 border-emerald-400/20' : 'bg-red-500/10 border-red-400/20'"
          >
            <div class="text-xs text-slate-400">净收益</div>
            <div
              class="text-lg font-bold"
              :class="backtestResult.net_profit >= 0 ? 'text-emerald-300' : 'text-red-300'"
            >
              {{ backtestResult.net_profit >= 0 ? '+' : '' }}{{ formatMoney(backtestResult.net_profit) }}
            </div>
          </div>
        </div>

        <!-- LLM 分析 -->
        <div v-if="backtestResult.analysis" class="p-4 rounded-xl bg-white/5 border border-white/10">
          <div class="text-xs text-slate-400 mb-2">AI 分析</div>
          <p class="text-sm text-slate-300 leading-relaxed">{{ backtestResult.analysis }}</p>
        </div>
      </div>

      <!-- 多模型回测结果 -->
      <div v-if="backtestResult && backtestResult.multi" class="space-y-4">
        <!-- 实际开奖（共享） -->
        <div class="p-4 rounded-xl bg-slate-500/10 border border-slate-400/20">
          <div class="text-xs text-slate-400 mb-2">
            实际开奖 · {{ backtestResult.target_issue }} ({{ backtestResult.target_date }})
          </div>
          <BallDisplay :red-balls="backtestResult.actual_red_balls" :blue-balls="backtestResult.actual_blue_balls" />
        </div>

        <!-- 模型对比表 -->
        <div class="overflow-x-auto rounded-xl border border-white/10">
          <table class="w-full text-sm">
            <thead class="bg-white/5 text-slate-300">
              <tr>
                <th class="px-3 py-2 text-left">模型</th>
                <th class="px-3 py-2 text-center">注数</th>
                <th class="px-3 py-2 text-right">总花费</th>
                <th class="px-3 py-2 text-right">总中奖</th>
                <th class="px-3 py-2 text-right">净收益</th>
                <th class="px-3 py-2 text-center">最佳命中</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="r in backtestResult.results"
                :key="r.model"
                class="border-t border-white/5"
                :class="r.error ? 'bg-red-500/5' : (r.net_profit > 0 ? 'bg-emerald-500/5' : '')"
              >
                <td class="px-3 py-2">
                  <span class="font-bold text-slate-200">{{ r.model }}</span>
                  <span v-if="r.error" class="ml-2 text-xs text-red-300">{{ r.error }}</span>
                </td>
                <td class="px-3 py-2 text-center text-slate-300">{{ r.predictions.length }}</td>
                <td class="px-3 py-2 text-right text-slate-300">{{ r.total_cost }}元</td>
                <td class="px-3 py-2 text-right text-amber-300">{{ formatMoney(r.total_winnings) }}</td>
                <td
                  class="px-3 py-2 text-right font-bold"
                  :class="r.net_profit >= 0 ? 'text-emerald-300' : 'text-red-300'"
                >
                  {{ r.net_profit >= 0 ? '+' : '' }}{{ formatMoney(r.net_profit) }}
                </td>
                <td class="px-3 py-2 text-center">
                  <span v-if="r.best_level > 0" class="text-amber-300 font-bold">第{{ r.best_level }}等</span>
                  <span v-else class="text-slate-500">-</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- 每个模型的详细预测 -->
        <div
          v-for="r in backtestResult.results"
          :key="r.model"
          class="rounded-xl border border-white/10 overflow-hidden"
        >
          <div class="px-4 py-2 bg-white/5 border-b border-white/10 flex items-center justify-between">
            <span class="text-sm font-bold text-slate-200">{{ r.model }}</span>
            <span
              v-if="r.used_llm"
              class="text-[10px] px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300"
            >LLM</span>
          </div>
          <div v-if="r.error" class="p-4 text-sm text-red-300">{{ r.error }}</div>
          <div v-else class="p-3 space-y-2">
            <div
              v-for="(pred, idx) in r.predictions"
              :key="idx"
              class="p-3 rounded-lg border"
              :class="predPrizeCardClass(pred.prize.level)"
            >
              <div class="flex items-center justify-between mb-2 text-xs">
                <span class="text-slate-400">第 {{ idx + 1 }} 注 · {{ pred.prize.desc }}</span>
                <span v-if="pred.prize.amount > 0" class="text-amber-300 font-bold">{{ formatMoney(pred.prize.amount) }}</span>
              </div>
              <BallDisplay :red-balls="pred.red_balls" :blue-balls="pred.blue_balls" />
              <div class="mt-2 text-xs text-slate-400">
                前区 {{ pred.prize.red_hits }}/5 · 后区 {{ pred.prize.blue_hits }}/2
              </div>
              <div v-if="pred.reason" class="mt-1 text-xs text-slate-500">
                <span class="text-violet-300">理由：</span>{{ pred.reason }}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- ========== 2. 固定号码长期模拟 ========== -->
    <div v-show="subActive === 'simulate'">
      <p class="text-xs text-slate-500 mb-4">
        输入一组号码，模拟在<strong class="text-slate-300">所有历史期</strong>持续购买，统计累计中奖概率和收益。
      </p>

      <!-- 号码输入 -->
      <div class="p-4 rounded-xl bg-white/5 border border-white/10 mb-4">
        <div class="mb-3">
          <label class="block text-xs text-slate-400 mb-2">前区(5个，01-35)</label>
          <div class="flex flex-wrap gap-2">
            <input
              v-for="(_, i) in simReds"
              :key="'r' + i"
              v-model="simReds[i]"
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
              v-for="(_, i) in simBlues"
              :key="'b' + i"
              v-model="simBlues[i]"
              type="text"
              maxlength="2"
              placeholder="00"
              class="w-12 h-12 text-center text-lg font-bold bg-blue-500/20 border border-blue-400/30 rounded-lg text-blue-200 outline-none focus:border-blue-400"
            />
          </div>
        </div>
        <div class="flex gap-2">
          <button
            @click="runSimulate"
            :disabled="simLoading"
            class="px-5 py-2 rounded-lg bg-violet-500 hover:bg-violet-600 text-white text-sm font-bold transition disabled:opacity-50"
          >
            {{ simLoading ? '计算中...' : '开始模拟' }}
          </button>
          <button
            @click="fillRandom"
            class="px-4 py-2 rounded-lg bg-white/10 hover:bg-white/20 text-slate-300 text-sm transition"
          >
            随机填入
          </button>
        </div>
      </div>

      <!-- 模拟结果 -->
      <div v-if="simResult" class="space-y-4">
        <!-- 汇总卡片 -->
        <div class="grid grid-cols-2 md:grid-cols-4 gap-3">
          <div class="p-3 rounded-xl bg-white/5 border border-white/10 text-center">
            <div class="text-xs text-slate-400">总投注</div>
            <div class="text-xl font-bold text-slate-200">{{ simResult.total_bets }}期</div>
          </div>
          <div class="p-3 rounded-xl bg-white/5 border border-white/10 text-center">
            <div class="text-xs text-slate-400">总花费</div>
            <div class="text-xl font-bold text-slate-200">{{ simResult.total_cost }}元</div>
          </div>
          <div class="p-3 rounded-xl bg-white/5 border border-white/10 text-center">
            <div class="text-xs text-slate-400">总中奖</div>
            <div class="text-xl font-bold text-amber-300">{{ formatMoney(simResult.total_winnings) }}</div>
          </div>
          <div
            class="p-3 rounded-xl border text-center"
            :class="simResult.net_profit >= 0 ? 'bg-emerald-500/10 border-emerald-400/20' : 'bg-red-500/10 border-red-400/20'"
          >
            <div class="text-xs text-slate-400">净收益</div>
            <div
              class="text-xl font-bold"
              :class="simResult.net_profit >= 0 ? 'text-emerald-300' : 'text-red-300'"
            >
              {{ simResult.net_profit >= 0 ? '+' : '' }}{{ formatMoney(simResult.net_profit) }}
            </div>
          </div>
        </div>

        <!-- 概率统计 -->
        <div class="grid grid-cols-1 md:grid-cols-3 gap-3">
          <div class="p-3 rounded-xl bg-white/5 border border-white/10 text-center">
            <div class="text-xs text-slate-400">中奖率</div>
            <div class="text-lg font-bold text-slate-200">{{ simResult.win_rate }}%</div>
            <div class="text-xs text-slate-500">{{ simResult.win_count }}/{{ simResult.total_bets }}期</div>
          </div>
          <div class="p-3 rounded-xl bg-white/5 border border-white/10 text-center">
            <div class="text-xs text-slate-400">投资回报率</div>
            <div
              class="text-lg font-bold"
              :class="simResult.roi >= 0 ? 'text-emerald-300' : 'text-red-300'"
            >
              {{ simResult.roi >= 0 ? '+' : '' }}{{ simResult.roi }}%
            </div>
          </div>
          <div class="p-3 rounded-xl bg-white/5 border border-white/10 text-center">
            <div class="text-xs text-slate-400">每注成本</div>
            <div class="text-lg font-bold text-slate-200">2元</div>
          </div>
        </div>

        <!-- 中奖分布 -->
        <div v-if="Object.keys(simResult.level_stats).length" class="p-4 rounded-xl bg-white/5 border border-white/10">
          <div class="text-xs text-slate-400 mb-2">中奖等级分布</div>
          <div class="flex flex-wrap gap-2">
            <span
              v-for="(count, level) in simResult.level_stats"
              :key="level"
              class="px-3 py-1 rounded-full text-xs"
              :class="levelColor(level)"
            >
              {{ level }} × {{ count }}
            </span>
          </div>
        </div>

        <!-- 每期明细 -->
        <div class="overflow-x-auto rounded-xl border border-white/10 max-h-80 overflow-y-auto">
          <table class="w-full text-sm whitespace-nowrap">
            <thead class="sticky top-0 bg-slate-800/95">
              <tr class="text-slate-300">
                <th class="px-3 py-2 text-left">期号</th>
                <th class="px-3 py-2 text-left">开奖号码</th>
                <th class="px-3 py-2 text-center">命中</th>
                <th class="px-3 py-2 text-right">奖金</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="d in simResult.draws"
                :key="d.issue"
                class="border-t border-white/5"
                :class="d.level > 0 ? 'bg-amber-500/5' : ''"
              >
                <td class="px-3 py-2 text-slate-300 tabular-nums">{{ d.issue }}</td>
                <td class="px-3 py-2">
                  <span class="text-red-300">{{ d.actual_red_balls.join(',') }}</span>
                  <span class="text-slate-500 mx-1">+</span>
                  <span class="text-blue-300">{{ d.actual_blue_balls.join(',') }}</span>
                </td>
                <td class="px-3 py-2 text-center tabular-nums">
                  <span :class="d.level > 0 ? 'text-amber-300 font-bold' : 'text-slate-500'">
                    {{ d.red_hits }}+{{ d.blue_hits }}
                  </span>
                </td>
                <td class="px-3 py-2 text-right tabular-nums">
                  <span :class="d.amount > 0 ? 'text-amber-300' : 'text-slate-500'">
                    {{ d.amount > 0 ? formatMoney(d.amount) : '-' }}
                  </span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- ========== 3. AI 预测 + 长期固定购买模拟 ========== -->
    <div v-show="subActive === 'ai-simulate'">
      <div class="flex flex-wrap items-end gap-3 mb-4">
        <div>
          <label class="block text-xs text-slate-400 mb-1">选择起始期号</label>
          <USelect
            v-model="aiSimIssue"
            :options="issueOptions"
            class="w-[200px]"
          />
        </div>
        <div>
          <label class="block text-xs text-slate-400 mb-1">加注数</label>
          <USelect
            v-model="aiSimCount"
            :options="[{value:1,label:'1 注'},{value:3,label:'3 注'},{value:5,label:'5 注'},{value:10,label:'10 注'}]"
            class="w-[120px]"
          />
        </div>
        <div>
          <label class="block text-xs text-slate-400 mb-1">预测模型</label>
          <ModelSelector v-model="aiSimModels" />
        </div>
        <button
          @click="runAiSimulate"
          :disabled="!aiSimIssue || aiSimLoading"
          class="px-5 py-2 rounded-lg bg-violet-500 hover:bg-violet-600 text-white text-sm font-bold transition disabled:opacity-50"
        >
          {{ aiSimLoading ? 'AI 分析中...' : '开始模拟' }}
        </button>
      </div>
      <p class="text-xs text-slate-500 mb-4">
        AI 基于所选期号<strong class="text-slate-300">之前</strong>的历史数据生成 <strong class="text-violet-300">{{ aiSimCount }} 组</strong>号码，然后从该期开始<strong class="text-slate-300">一直买到最新一期</strong>，每期购买全部注数，统计累计收益。可选多模型对比。
      </p>

      <!-- 单模型结果 -->
      <div v-if="aiSimResult && !aiSimResult.multi" class="space-y-4">
        <!-- AI 预测的号码(可能多注) -->
        <div class="space-y-3">
          <div
            v-for="(pred, idx) in aiSimResult.predictions"
            :key="idx"
            class="p-4 rounded-xl bg-violet-500/10 border border-violet-400/20"
          >
            <div class="flex items-center justify-between mb-2">
              <span class="text-xs text-slate-400">
                AI 预测号码(固定购买)
                <span v-if="aiSimResult.predictions.length > 1" class="ml-1 text-violet-300">第 {{ idx + 1 }} 注</span>
              </span>
              <span
                class="text-[10px] px-2 py-0.5 rounded-full"
                :class="pred.used_llm ? 'bg-emerald-500/20 text-emerald-300' : 'bg-slate-500/20 text-slate-400'"
              >
                {{ pred.used_llm ? pred.llm_model : '启发式' }}
              </span>
            </div>
            <BallDisplay :red-balls="pred.red_balls" :blue-balls="pred.blue_balls" />
            <div v-if="pred.reason" class="mt-2 text-xs text-slate-400">
              <span class="text-violet-300">理由：</span>{{ pred.reason }}
            </div>
          </div>
        </div>

        <!-- AI 分析 -->
        <div v-if="aiSimResult.analysis" class="p-4 rounded-xl bg-white/5 border border-white/10">
          <div class="text-xs text-slate-400 mb-2">AI 分析</div>
          <p class="text-sm text-slate-300 leading-relaxed">{{ aiSimResult.analysis }}</p>
        </div>

        <!-- 汇总卡片 -->
        <div class="grid grid-cols-2 md:grid-cols-4 gap-3">
          <div class="p-3 rounded-xl bg-white/5 border border-white/10 text-center">
            <div class="text-xs text-slate-400">持续购买</div>
            <div class="text-xl font-bold text-slate-200">{{ aiSimResult.simulation.total_bets }}期</div>
            <div class="text-[10px] text-slate-500">{{ aiSimResult.simulation.range.start_issue }} ~ {{ aiSimResult.simulation.range.end_issue }}</div>
          </div>
          <div class="p-3 rounded-xl bg-white/5 border border-white/10 text-center">
            <div class="text-xs text-slate-400">总花费</div>
            <div class="text-xl font-bold text-slate-200">{{ aiSimResult.simulation.total_cost }}元</div>
            <div class="text-[10px] text-slate-500">{{ aiSimResult.simulation.bet_per_period }}注/期 × {{ aiSimResult.simulation.total_bets }}期</div>
          </div>
          <div class="p-3 rounded-xl bg-white/5 border border-white/10 text-center">
            <div class="text-xs text-slate-400">总中奖</div>
            <div class="text-xl font-bold text-amber-300">{{ formatMoney(aiSimResult.simulation.total_winnings) }}</div>
          </div>
          <div
            class="p-3 rounded-xl border text-center"
            :class="aiSimResult.simulation.net_profit >= 0 ? 'bg-emerald-500/10 border-emerald-400/20' : 'bg-red-500/10 border-red-400/20'"
          >
            <div class="text-xs text-slate-400">净收益</div>
            <div
              class="text-xl font-bold"
              :class="aiSimResult.simulation.net_profit >= 0 ? 'text-emerald-300' : 'text-red-300'"
            >
              {{ aiSimResult.simulation.net_profit >= 0 ? '+' : '' }}{{ formatMoney(aiSimResult.simulation.net_profit) }}
            </div>
          </div>
        </div>

        <!-- 概率统计 -->
        <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
          <div class="p-3 rounded-xl bg-white/5 border border-white/10 text-center">
            <div class="text-xs text-slate-400">中奖率</div>
            <div class="text-lg font-bold text-slate-200">{{ aiSimResult.simulation.win_rate }}%</div>
            <div class="text-xs text-slate-500">{{ aiSimResult.simulation.win_count }}/{{ aiSimResult.simulation.total_bets }}期</div>
          </div>
          <div class="p-3 rounded-xl bg-white/5 border border-white/10 text-center">
            <div class="text-xs text-slate-400">投资回报率</div>
            <div
              class="text-lg font-bold"
              :class="aiSimResult.simulation.roi >= 0 ? 'text-emerald-300' : 'text-red-300'"
            >
              {{ aiSimResult.simulation.roi >= 0 ? '+' : '' }}{{ aiSimResult.simulation.roi }}%
            </div>
          </div>
        </div>

        <!-- 中奖分布 -->
        <div v-if="Object.keys(aiSimResult.simulation.level_stats).length" class="p-4 rounded-xl bg-white/5 border border-white/10">
          <div class="text-xs text-slate-400 mb-2">中奖等级分布(每期最佳命中)</div>
          <div class="flex flex-wrap gap-2">
            <span
              v-for="(count, level) in aiSimResult.simulation.level_stats"
              :key="level"
              class="px-3 py-1 rounded-full text-xs"
              :class="levelColor(level)"
            >
              {{ level }} × {{ count }}
            </span>
          </div>
        </div>

        <!-- 每期明细 -->
        <div class="overflow-x-auto rounded-xl border border-white/10 max-h-80 overflow-y-auto">
          <table class="w-full text-sm whitespace-nowrap">
            <thead class="sticky top-0 bg-slate-800/95">
              <tr class="text-slate-300">
                <th class="px-3 py-2 text-left">期号</th>
                <th class="px-3 py-2 text-left">开奖号码</th>
                <th class="px-3 py-2 text-center">最佳命中</th>
                <th class="px-3 py-2 text-right">总奖金</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="d in aiSimResult.simulation.draws"
                :key="d.issue"
                class="border-t border-white/5"
                :class="d.best_level > 0 ? 'bg-amber-500/5' : ''"
              >
                <td class="px-3 py-2 text-slate-300 tabular-nums">{{ d.issue }}</td>
                <td class="px-3 py-2">
                  <span class="text-red-300">{{ d.actual_red_balls.join(',') }}</span>
                  <span class="text-slate-500 mx-1">+</span>
                  <span class="text-blue-300">{{ d.actual_blue_balls.join(',') }}</span>
                </td>
                <td class="px-3 py-2 text-center tabular-nums">
                  <span :class="d.best_level > 0 ? 'text-amber-300 font-bold' : 'text-slate-500'">
                    {{ d.best_desc }}
                  </span>
                </td>
                <td class="px-3 py-2 text-right tabular-nums">
                  <span :class="d.amount > 0 ? 'text-amber-300' : 'text-slate-500'">
                    {{ d.amount > 0 ? formatMoney(d.amount) : '-' }}
                  </span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- 多模型结果 -->
      <div v-if="aiSimResult && aiSimResult.multi" class="space-y-4">
        <!-- 模型对比表 -->
        <div class="overflow-x-auto rounded-xl border border-white/10">
          <table class="w-full text-sm">
            <thead class="bg-white/5 text-slate-300">
              <tr>
                <th class="px-3 py-2 text-left">模型</th>
                <th class="px-3 py-2 text-center">期数</th>
                <th class="px-3 py-2 text-center">注/期</th>
                <th class="px-3 py-2 text-right">总花费</th>
                <th class="px-3 py-2 text-right">总中奖</th>
                <th class="px-3 py-2 text-right">净收益</th>
                <th class="px-3 py-2 text-right">ROI</th>
                <th class="px-3 py-2 text-center">中奖率</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="r in aiSimResult.results"
                :key="r.model"
                class="border-t border-white/5"
                :class="r.error ? 'bg-red-500/5' : (r.simulation && r.simulation.net_profit > 0 ? 'bg-emerald-500/5' : '')"
              >
                <td class="px-3 py-2">
                  <span class="font-bold text-slate-200">{{ r.model }}</span>
                  <span v-if="r.error" class="ml-2 text-xs text-red-300">{{ r.error }}</span>
                </td>
                <td class="px-3 py-2 text-center text-slate-300">{{ r.simulation?.total_bets ?? '-' }}</td>
                <td class="px-3 py-2 text-center text-slate-300">{{ r.simulation?.bet_per_period ?? '-' }}</td>
                <td class="px-3 py-2 text-right text-slate-300">{{ r.simulation?.total_cost ?? '-' }}元</td>
                <td class="px-3 py-2 text-right text-amber-300">{{ r.simulation ? formatMoney(r.simulation.total_winnings) : '-' }}</td>
                <td
                  class="px-3 py-2 text-right font-bold"
                  :class="r.simulation && r.simulation.net_profit >= 0 ? 'text-emerald-300' : 'text-red-300'"
                >
                  {{ r.simulation ? (r.simulation.net_profit >= 0 ? '+' : '') + formatMoney(r.simulation.net_profit) : '-' }}
                </td>
                <td
                  class="px-3 py-2 text-right"
                  :class="r.simulation && r.simulation.roi >= 0 ? 'text-emerald-300' : 'text-red-300'"
                >
                  {{ r.simulation ? (r.simulation.roi >= 0 ? '+' : '') + r.simulation.roi + '%' : '-' }}
                </td>
                <td class="px-3 py-2 text-center text-slate-300">{{ r.simulation?.win_rate ?? '-' }}%</td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- 每个模型的预测号码 + 分析 -->
        <div
          v-for="r in aiSimResult.results"
          :key="r.model"
          class="rounded-xl border border-white/10 overflow-hidden"
        >
          <div class="px-4 py-2 bg-white/5 border-b border-white/10 flex items-center justify-between">
            <span class="text-sm font-bold text-slate-200">{{ r.model }}</span>
            <span v-if="r.error" class="text-xs text-red-300">失败</span>
          </div>
          <div v-if="r.error" class="p-4 text-sm text-red-300">{{ r.error }}</div>
          <div v-else class="p-3 space-y-3">
            <!-- 预测号码 -->
            <div class="flex flex-wrap gap-2">
              <div
                v-for="(pred, idx) in r.predictions"
                :key="idx"
                class="p-2 rounded-lg bg-violet-500/10 border border-violet-400/20"
              >
                <div class="text-[10px] text-slate-400 mb-1">第{{ idx + 1 }}注</div>
                <BallDisplay :red-balls="pred.red_balls" :blue-balls="pred.blue_balls" />
              </div>
            </div>
            <div v-if="r.analysis" class="text-xs text-slate-400 leading-relaxed">
              <span class="text-violet-300">分析：</span>{{ r.analysis }}
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { api } from '../api.js'
import { useToast } from '../composables/useToast.js'
import BallDisplay from './BallDisplay.vue'
import ModelSelector from './ModelSelector.vue'
import USelect from './USelect.vue'

const toast = useToast()
const subTabs = [
  { id: 'backtest', name: 'AI 预测回测' },
  { id: 'simulate', name: '固定号码模拟' },
  { id: 'ai-simulate', name: 'AI 预测+长期模拟' },
]
const subActive = ref('backtest')

// --- 回测 ---
const issues = ref([])
const issueOptions = computed(() => issues.value.map(i => ({ value: i.issue, label: `${i.issue} (${i.date})` })))
const selectedIssue = ref('')
const backtestCount = ref(1)
const backtestModels = ref([])
const backtestLoading = ref(false)
const backtestResult = ref(null)

function predPrizeCardClass(level) {
  if (level === 0) return 'bg-slate-500/10 border-slate-400/20'
  if (level <= 2) return 'bg-amber-500/10 border-amber-400/30'
  if (level <= 4) return 'bg-violet-500/10 border-violet-400/30'
  return 'bg-emerald-500/10 border-emerald-400/20'
}

function predPrizeTextClass(level) {
  if (level <= 2) return 'text-amber-300'
  if (level <= 4) return 'text-violet-300'
  return 'text-emerald-300'
}

async function runBacktest() {
  backtestLoading.value = true
  backtestResult.value = null
  try {
    backtestResult.value = await api.backtestPredict(selectedIssue.value, backtestCount.value, backtestModels.value)
    const r = backtestResult.value
    if (r.multi) {
      const ok = r.results.filter(x => !x.error).length
      toast.success(`多模型回测完成: ${ok}/${r.results.length} 成功`)
    } else {
      toast.success(`回测完成: ${r.bet_count}注, 总中奖${formatMoney(r.total_winnings)}, 净收益${r.net_profit >= 0 ? '+' : ''}${formatMoney(r.net_profit)}`)
    }
  } catch (e) {
    toast.error('回测失败: ' + e.message)
  } finally {
    backtestLoading.value = false
  }
}

// --- 模拟 ---
const simReds = ref(['', '', '', '', ''])
const simBlues = ref(['', ''])
const simLoading = ref(false)
const simResult = ref(null)

function fillRandom() {
  const reds = new Set()
  while (reds.size < 5) reds.add(String(Math.floor(Math.random() * 35) + 1).padStart(2, '0'))
  const blues = new Set()
  while (blues.size < 2) blues.add(String(Math.floor(Math.random() * 12) + 1).padStart(2, '0'))
  simReds.value = [...reds].sort()
  simBlues.value = [...blues].sort()
}

async function runSimulate() {
  const reds = simReds.value.filter(Boolean)
  const blues = simBlues.value.filter(Boolean)
  if (reds.length !== 5 || blues.length !== 2) {
    toast.error('请输入5个前区号码和2个后区号码')
    return
  }
  simLoading.value = true
  simResult.value = null
  try {
    simResult.value = await api.simulateFixed(reds, blues)
    toast.success(`模拟完成: ${simResult.value.total_bets}期, 中奖率${simResult.value.win_rate}%`)
  } catch (e) {
    toast.error('模拟失败: ' + e.message)
  } finally {
    simLoading.value = false
  }
}

// --- AI 预测 + 长期模拟 ---
const aiSimIssue = ref('')
const aiSimCount = ref(1)
const aiSimModels = ref([])
const aiSimLoading = ref(false)
const aiSimResult = ref(null)

async function runAiSimulate() {
  aiSimLoading.value = true
  aiSimResult.value = null
  try {
    aiSimResult.value = await api.aiSimulate(aiSimIssue.value, aiSimCount.value, aiSimModels.value)
    if (aiSimResult.value.multi) {
      const ok = aiSimResult.value.results.filter(x => !x.error).length
      toast.success(`多模型模拟完成: ${ok}/${aiSimResult.value.results.length} 成功`)
    } else {
      const s = aiSimResult.value.simulation
      toast.success(`模拟完成: ${s.total_bets}期 × ${s.bet_per_period}注, 净收益${s.net_profit >= 0 ? '+' : ''}${formatMoney(s.net_profit)}`)
    }
  } catch (e) {
    toast.error('模拟失败: ' + e.message)
  } finally {
    aiSimLoading.value = false
  }
}

function formatMoney(n) {
  if (n >= 1_0000_0000) return (n / 1_0000_0000).toFixed(2) + '亿'
  if (n >= 1_0000) return (n / 1_0000).toFixed(1) + '万'
  return n + '元'
}

function levelColor(level) {
  if (level.includes('一等')) return 'bg-amber-500/20 text-amber-300'
  if (level.includes('二等')) return 'bg-orange-500/20 text-orange-300'
  if (level.includes('三等')) return 'bg-violet-500/20 text-violet-300'
  return 'bg-slate-500/20 text-slate-300'
}

async function loadIssues(preserveSelection = false) {
  try {
    const prevSelected = selectedIssue.value
    const prevAiSim = aiSimIssue.value
    issues.value = await api.getBacktestIssues(100)
    if (issues.value.length > 1) {
      if (preserveSelection && prevSelected && issues.value.some(i => i.issue === prevSelected)) {
        // 保留原选择
      } else {
        selectedIssue.value = issues.value[1].issue
      }
      if (preserveSelection && prevAiSim && issues.value.some(i => i.issue === prevAiSim)) {
        aiSimIssue.value = prevAiSim
      } else {
        const idx = Math.min(9, issues.value.length - 1)
        aiSimIssue.value = issues.value[idx].issue
      }
    }
  } catch (e) {
    toast.error('加载期号失败: ' + e.message)
  }
}

// 监听数据更新事件（开奖历史抓取最新后触发）
function onDataUpdated() {
  loadIssues(true)
}

onMounted(() => {
  loadIssues()
  window.addEventListener('lottery-data-updated', onDataUpdated)
})

onUnmounted(() => {
  window.removeEventListener('lottery-data-updated', onDataUpdated)
})
</script>
