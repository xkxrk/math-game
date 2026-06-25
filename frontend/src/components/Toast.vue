<template>
  <Teleport to="body">
    <Transition name="toast" tag="div">
      <div
        v-if="visible"
        class="fixed top-6 right-6 z-50 flex items-center gap-3 px-5 py-3 rounded-xl shadow-2xl backdrop-blur border text-sm font-medium max-w-sm"
        :class="typeClass"
      >
        <span class="text-lg">{{ icon }}</span>
        <span>{{ message }}</span>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { ref, computed, onBeforeUnmount } from 'vue'

const visible = ref(false)
const message = ref('')
const type = ref('info')
let timer = null

const typeClass = computed(() => ({
  'bg-emerald-500/90 border-emerald-400 text-white': type.value === 'success',
  'bg-red-500/90 border-red-400 text-white': type.value === 'error',
  'bg-slate-700/90 border-slate-500 text-slate-100': type.value === 'info',
}))

const icon = computed(() => {
  if (type.value === 'success') return '\u2713'
  if (type.value === 'error') return '\u2717'
  return '\u24D8'
})

function show(msg, t = 'info') {
  message.value = msg
  type.value = t
  visible.value = true
  if (timer) clearTimeout(timer)
  timer = setTimeout(() => {
    visible.value = false
  }, 3500)
}

defineExpose({ show })
onBeforeUnmount(() => {
  if (timer) clearTimeout(timer)
})
</script>

<style scoped>
.toast-enter-active,
.toast-leave-active {
  transition: all 0.3s ease;
}
.toast-enter-from,
.toast-leave-to {
  opacity: 0;
  transform: translateX(60px);
}
</style>
