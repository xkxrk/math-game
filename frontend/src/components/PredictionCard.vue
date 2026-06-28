<template>
  <div>
    <div class="flex items-center justify-between mb-2">
      <label class="flex items-center gap-2 cursor-pointer">
        <input
          type="checkbox"
          :checked="pred.selected"
          @change="$emit('toggle')"
          class="w-4 h-4 accent-violet-500"
        />
        <span class="text-xs text-slate-400">第 {{ idx + 1 }} 注</span>
      </label>
      <div class="flex items-center gap-2">
        <span
          v-if="model"
          class="px-2 py-0.5 rounded-full bg-fuchsia-500/20 text-fuchsia-300 text-[10px]"
        >{{ model }}</span>
        <span
          class="text-[10px] px-2 py-0.5 rounded-full"
          :class="pred.used_llm ? 'bg-emerald-500/20 text-emerald-300' : 'bg-slate-500/20 text-slate-400'"
        >
          {{ pred.used_llm ? 'LLM' : '启发式' }}
        </span>
      </div>
    </div>
    <BallDisplay :red-balls="pred.red_balls" :blue-balls="pred.blue_balls" />
    <div v-if="pred.reason" class="mt-2 text-xs text-slate-400 leading-relaxed">
      <span class="text-violet-300">理由：</span>{{ pred.reason }}
    </div>
    <button
      @click="$emit('adopt')"
      :disabled="adopting"
      class="mt-3 px-4 py-1.5 rounded-lg bg-violet-500 hover:bg-violet-600 text-white text-xs font-bold transition disabled:opacity-50"
    >
      {{ adopting ? '采纳中...' : '采纳此号码' }}
    </button>
  </div>
</template>

<script setup>
import BallDisplay from './BallDisplay.vue'

defineProps({
  pred: { type: Object, required: true },
  idx: { type: Number, default: 0 },
  adopting: { type: Boolean, default: false },
  model: { type: String, default: '' },
})

defineEmits(['toggle', 'adopt'])
</script>
