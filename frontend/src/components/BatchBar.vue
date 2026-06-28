<template>
  <div
    v-if="predictions.length > 1"
    class="flex items-center justify-between gap-3 p-3 rounded-xl bg-white/5 border border-white/10"
  >
    <label class="flex items-center gap-2 cursor-pointer text-sm text-slate-300">
      <input
        type="checkbox"
        :checked="allSelected"
        @change="$emit('toggle-all', $event.target.checked)"
        class="w-4 h-4 accent-violet-500"
      />
      全选 ({{ selectedCount }}/{{ predictions.length }})
    </label>
    <button
      @click="$emit('adopt-selected')"
      :disabled="selectedCount === 0 || batchAdopting"
      class="px-4 py-1.5 rounded-lg bg-emerald-500 hover:bg-emerald-600 text-white text-xs font-bold transition disabled:opacity-50"
    >
      {{ batchAdopting ? `采纳中(${adoptProgress}/${selectedCount})...` : `采纳选中 (${selectedCount})` }}
    </button>
  </div>
</template>

<script setup>
defineProps({
  predictions: { type: Array, default: () => [] },
  allSelected: { type: Boolean, default: false },
  selectedCount: { type: Number, default: 0 },
  batchAdopting: { type: Boolean, default: false },
  adoptProgress: { type: Number, default: 0 },
})

defineEmits(['toggle-all', 'adopt-selected'])
</script>
