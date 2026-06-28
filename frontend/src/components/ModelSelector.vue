<template>
  <div class="relative inline-block" ref="rootRef">
    <button
      type="button"
      @click="open = !open"
      class="inline-flex items-center gap-2 bg-white/10 hover:bg-white/20 border border-white/20 rounded-lg px-3 h-[40px] text-sm text-slate-100 outline-none transition w-[240px]"
    >
      <svg class="w-4 h-4 opacity-70 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/>
        <polyline points="3.27 6.96 12 12.01 20.73 6.96"/>
        <line x1="12" y1="22.08" x2="12" y2="12"/>
      </svg>
      <span class="flex-1 min-w-0 text-left truncate">{{ buttonText }}</span>
      <span
        v-if="selected.length"
        class="shrink-0 px-1.5 py-0.5 rounded-full bg-violet-500 text-white text-[10px] font-bold tabular-nums"
      >
        {{ selected.length }}
      </span>
    </button>

    <div
      v-show="open"
      class="absolute z-50 mt-2 w-72 max-h-80 overflow-y-auto rounded-xl bg-slate-800 border border-white/20 shadow-xl p-2"
    >
      <div class="flex items-center justify-between px-2 py-1 mb-1 border-b border-white/10">
        <span class="text-xs text-slate-400">选择模型</span>
        <div class="flex gap-2 text-[11px]">
          <button type="button" @click="selectAll" class="text-violet-300 hover:text-violet-200">全选</button>
          <button type="button" @click="clearAll" class="text-slate-400 hover:text-slate-300">清空</button>
        </div>
      </div>

      <!-- 云模型分组 -->
      <div v-if="cloudModels.length" class="mb-2">
        <div class="px-2 py-1 text-[10px] text-slate-500 uppercase tracking-wider flex items-center gap-1">
          <svg class="w-3 h-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M18 10h-1.26A8 8 0 1 0 9 20h9a5 5 0 0 0 0-10z"/>
          </svg>
          云模型（无需下载）
        </div>
        <label
          v-for="m in cloudModels"
          :key="m.name"
          class="flex items-center gap-2 px-2 py-1.5 rounded-lg hover:bg-white/5 cursor-pointer"
        >
          <input
            type="checkbox"
            :value="m.name"
            v-model="selected"
            class="w-4 h-4 accent-violet-500"
          />
          <div class="flex-1 min-w-0">
            <div class="text-sm text-slate-100 truncate">{{ m.name }}</div>
            <div v-if="m.desc" class="text-[10px] text-slate-500 truncate">{{ m.desc }}</div>
          </div>
          <span class="px-1.5 py-0.5 rounded-full bg-sky-500/20 text-sky-300 text-[9px] font-bold">CLOUD</span>
        </label>
      </div>

      <!-- 本地已安装模型 -->
      <div v-if="localModels.length" class="mb-2">
        <div class="px-2 py-1 text-[10px] text-slate-500 uppercase tracking-wider flex items-center gap-1">
          <svg class="w-3 h-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <rect x="2" y="3" width="20" height="14" rx="2" ry="2"/>
            <line x1="8" y1="21" x2="16" y2="21"/>
            <line x1="12" y1="17" x2="12" y2="21"/>
          </svg>
          本地已安装
        </div>
        <label
          v-for="m in localModels"
          :key="m.name"
          class="flex items-center gap-2 px-2 py-1.5 rounded-lg hover:bg-white/5 cursor-pointer"
        >
          <input
            type="checkbox"
            :value="m.name"
            v-model="selected"
            class="w-4 h-4 accent-violet-500"
          />
          <div class="flex-1 min-w-0">
            <div class="text-sm text-slate-100 truncate">{{ m.name }}</div>
            <div v-if="m.details?.parameter_size" class="text-[10px] text-slate-500">
              {{ m.details.parameter_size }} · {{ m.details.quantization_level || m.details.family || '' }}
            </div>
          </div>
          <span v-if="m.size" class="text-[10px] text-slate-500">{{ formatSize(m.size) }}</span>
        </label>
      </div>
      <div v-else-if="loading" class="mb-2 px-2 py-1.5 text-xs text-slate-500">
        本地模型加载中...
      </div>

      <!-- 用户自定义模型 -->
      <div v-if="customModels.length" class="mb-2">
        <div class="px-2 py-1 text-[10px] text-slate-500 uppercase tracking-wider">
          自定义模型
        </div>
        <label
          v-for="m in customModels"
          :key="m.name"
          class="flex items-center gap-2 px-2 py-1.5 rounded-lg hover:bg-white/5 cursor-pointer group"
        >
          <input
            type="checkbox"
            :value="m.name"
            v-model="selected"
            class="w-4 h-4 accent-violet-500"
          />
          <div class="flex-1 min-w-0">
            <div class="text-sm text-slate-100 truncate">{{ m.name }}</div>
          </div>
          <button
            type="button"
            @click.prevent="removeCustom(m.name)"
            class="opacity-0 group-hover:opacity-100 text-red-400 hover:text-red-300 text-xs"
            title="移除"
          >×</button>
        </label>
      </div>

      <!-- 空状态 -->
      <div v-if="!cloudModels.length && !localModels.length && !customModels.length" class="px-2 py-3 text-xs text-slate-500 text-center">
        {{ loading ? '加载中...' : (errorMsg || '暂无可用模型' ) }}
      </div>

      <!-- 手动添加 -->
      <div class="mt-2 pt-2 border-t border-white/10">
        <div class="flex gap-1">
          <input
            v-model="customModel"
            @keyup.enter="addCustom"
            placeholder="输入模型名，回车添加"
            class="flex-1 bg-white/5 border border-white/10 rounded-lg px-2 py-1.5 text-xs text-slate-100 outline-none focus:border-violet-400"
          />
          <button
            type="button"
            @click="addCustom"
            :disabled="!customModel.trim()"
            class="px-2 py-1.5 rounded-lg bg-violet-500/30 hover:bg-violet-500/50 text-violet-200 text-xs transition disabled:opacity-30"
          >添加</button>
        </div>
        <div v-if="customModel.trim()" class="mt-1 text-[10px] text-slate-500">
          添加 "{{ customModel.trim() }}" 到自定义列表
        </div>
      </div>

      <div class="mt-2 pt-2 border-t border-white/10 text-[11px] text-slate-500 px-1 leading-relaxed">
        选 1 个=单模型预测；选多个=多模型对比<br>
        云模型通过 Ollama 订阅调用，无需下载
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { api } from '../api.js'

const props = defineProps({
  modelValue: { type: Array, default: () => [] },
})
const emit = defineEmits(['update:modelValue'])

const open = ref(false)
const loading = ref(false)
const errorMsg = ref('')
const localModels = ref([])  // Ollama 本地已安装
const customModels = ref([]) // 用户自定义（localStorage 持久化）
const selected = ref([...props.modelValue])
const customModel = ref('')
const rootRef = ref(null)

// Ollama 云模型预设（无需下载，通过订阅调用）
const CLOUD_PRESETS = [
  { name: 'glm-4.7:cloud', desc: '智谱 GLM-4.7' },
  { name: 'nemotron-3-super:cloud', desc: 'NVIDIA Nemotron-3-Super' },
  { name: 'gpt-oss:120b:cloud', desc: 'OpenAI GPT-OSS 120B' },
  { name: 'gpt-oss:20b:cloud', desc: 'OpenAI GPT-OSS 20B' },
  { name: 'deepseek-r1:cloud', desc: 'DeepSeek R1' },
  { name: 'deepseek-v3.1:cloud', desc: 'DeepSeek V3.1' },
  { name: 'qwen3:cloud', desc: 'Qwen3' },
  { name: 'llama3.1:cloud', desc: 'Llama 3.1' },
  { name: 'mistral-small3.1:cloud', desc: 'Mistral Small 3.1' },
  { name: 'phi4:cloud', desc: 'Microsoft Phi-4' },
  { name: 'gemma3:cloud', desc: 'Google Gemma 3' },
  { name: 'command-r:cloud', desc: 'Cohere Command-R' },
]

// 云模型列表（排除已安装的本地模型，避免重复）
const cloudModels = computed(() => {
  const localNames = new Set(localModels.value.map(m => m.name))
  const customNames = new Set(customModels.value.map(m => m.name))
  return CLOUD_PRESETS.filter(m => !localNames.has(m.name) && !customNames.has(m.name))
})

const buttonText = computed(() => {
  if (!selected.value.length) return '默认模型'
  if (selected.value.length === 1) return selected.value[0]
  return `${selected.value[0]} +${selected.value.length - 1}`
})

watch(() => props.modelValue, (v) => {
  selected.value = [...(v || [])]
})

watch(selected, (v) => {
  emit('update:modelValue', [...v])
}, { deep: true })

async function loadModels() {
  loading.value = true
  errorMsg.value = ''
  try {
    const r = await api.getOllamaModels()
    if (r.ok) {
      localModels.value = r.models || []
    } else {
      errorMsg.value = r.error || '获取本地模型失败'
    }
  } catch (e) {
    errorMsg.value = e.message
  } finally {
    loading.value = false
  }
}

function loadCustomModels() {
  // localStorage 同步读取，提前加载避免面板内容突变
  try {
    const saved = JSON.parse(localStorage.getItem('custom_models') || '[]')
    customModels.value = saved.map(name => ({ name, desc: '' }))
  } catch {
    customModels.value = []
  }
}

function selectAll() {
  const all = [
    ...cloudModels.value.map(m => m.name),
    ...localModels.value.map(m => m.name),
    ...customModels.value.map(m => m.name),
  ]
  selected.value = all
}

function clearAll() {
  selected.value = []
}

function addCustom() {
  const name = customModel.value.trim()
  if (!name) return
  // 避免重复
  const exists = [
    ...cloudModels.value,
    ...localModels.value,
    ...customModels.value,
  ].some(m => m.name === name)
  if (!exists) {
    customModels.value.push({ name, desc: '' })
    saveCustomModels()
  }
  if (!selected.value.includes(name)) {
    selected.value.push(name)
  }
  customModel.value = ''
}

function removeCustom(name) {
  customModels.value = customModels.value.filter(m => m.name !== name)
  selected.value = selected.value.filter(n => n !== name)
  saveCustomModels()
}

function saveCustomModels() {
  const names = customModels.value.map(m => m.name)
  localStorage.setItem('custom_models', JSON.stringify(names))
}

function formatSize(bytes) {
  if (!bytes) return ''
  if (bytes >= 1e9) return (bytes / 1e9).toFixed(1) + 'GB'
  if (bytes >= 1e6) return (bytes / 1e6).toFixed(0) + 'MB'
  return (bytes / 1e3).toFixed(0) + 'KB'
}

function handleClickOutside(e) {
  if (rootRef.value && !rootRef.value.contains(e.target)) {
    open.value = false
  }
}

onMounted(() => {
  loadCustomModels()
  loadModels()
  document.addEventListener('click', handleClickOutside)
})

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
})
</script>
