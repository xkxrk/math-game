<template>
  <div class="relative" ref="rootRef">
    <button
      type="button"
      ref="triggerRef"
      @click="toggle"
      :disabled="disabled"
      class="w-full flex items-center justify-between bg-white/10 border border-white/20 rounded-lg px-3 py-2 text-sm text-slate-100 outline-none transition hover:bg-white/20 disabled:opacity-50"
    >
      <span class="truncate text-left flex-1 min-w-0">{{ currentLabel }}</span>
      <svg
        class="w-4 h-4 opacity-60 shrink-0 ml-2 transition-transform"
        :class="open ? 'rotate-180' : ''"
        viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
      >
        <polyline points="6 9 12 15 18 9"/>
      </svg>
    </button>
    <Teleport to="body">
      <div
        v-show="open"
        ref="panelRef"
        class="fixed z-[100] w-max max-w-[320px] max-h-60 overflow-y-auto rounded-lg bg-slate-800 border border-white/20 shadow-xl py-1"
        :style="panelStyle"
      >
        <button
          v-for="opt in options"
          :key="opt.value"
          type="button"
          @click="choose(opt)"
          :class="[
            'w-full text-left px-3 py-1.5 text-sm transition whitespace-nowrap',
            opt.value === modelValue ? 'bg-violet-500/30 text-violet-200 font-bold' : 'text-slate-200 hover:bg-white/10',
          ]"
        >
          {{ opt.label }}
        </button>
        <div v-if="!options.length" class="px-3 py-2 text-xs text-slate-500 text-center">暂无选项</div>
      </div>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick, watch } from 'vue'

const props = defineProps({
  modelValue: { type: [String, Number], default: '' },
  options: { type: Array, default: () => [] },
  placeholder: { type: String, default: '请选择' },
  disabled: { type: Boolean, default: false },
  alignRight: { type: Boolean, default: false },
})
const emit = defineEmits(['update:modelValue', 'change'])

const open = ref(false)
const rootRef = ref(null)
const triggerRef = ref(null)
const panelRef = ref(null)
const panelStyle = ref({})

const currentLabel = computed(() => {
  const opt = props.options.find(o => o.value === props.modelValue)
  return opt ? opt.label : props.placeholder
})

// 定位面板：默认左对齐触发器左边；alignRight 时右边界对齐触发器右边
function positionPanel() {
  if (!open.value || !triggerRef.value || !panelRef.value) return
  const rect = triggerRef.value.getBoundingClientRect()
  const panelW = panelRef.value.offsetWidth || rect.width
  let left
  if (props.alignRight) {
    // 右对齐：面板右边 = 触发器右边
    left = rect.right - Math.max(panelW, rect.width)
    if (left < 8) left = 8
  } else {
    // 左对齐：面板左边 = 触发器左边
    left = rect.left
    if (left + panelW > window.innerWidth - 8) {
      left = Math.max(8, window.innerWidth - panelW - 8)
    }
  }
  panelStyle.value = {
    top: `${rect.bottom + 4}px`,
    left: `${left}px`,
    minWidth: `${rect.width}px`,
  }
}

function toggle() {
  open.value = !open.value
}

function choose(opt) {
  emit('update:modelValue', opt.value)
  emit('change', opt.value)
  open.value = false
}

function handleClickOutside(e) {
  if (rootRef.value && rootRef.value.contains(e.target)) return
  if (panelRef.value && panelRef.value.contains(e.target)) return
  open.value = false
}

watch(open, async (v) => {
  if (v) {
    await nextTick()
    positionPanel()
  }
})

onMounted(() => {
  document.addEventListener('click', handleClickOutside)
  window.addEventListener('resize', positionPanel)
  window.addEventListener('scroll', positionPanel, true)
})
onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
  window.removeEventListener('resize', positionPanel)
  window.removeEventListener('scroll', positionPanel, true)
})
</script>
