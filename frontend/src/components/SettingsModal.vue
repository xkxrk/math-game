<template>
  <transition name="fade">
    <div
      v-if="visible"
      class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm"
    >
      <div class="w-full max-w-md rounded-2xl bg-slate-900 border border-white/10 shadow-2xl max-h-[90vh] overflow-y-auto">
        <!-- 头部 -->
        <div class="flex items-center justify-between px-5 py-4 border-b border-white/10 sticky top-0 bg-slate-900 z-10">
          <h3 class="text-base font-bold text-slate-100">模型设置</h3>
          <button
            @click="close"
            class="text-slate-400 hover:text-slate-200 text-xl leading-none"
          >
            ×
          </button>
        </div>

        <!-- 内容 -->
        <div class="p-5 space-y-4">
          <!-- 当前状态徽标 -->
          <div
            class="flex items-center justify-between p-3 rounded-lg"
            :class="config.llm_api_key ? 'bg-emerald-500/10 border border-emerald-400/20' : 'bg-amber-500/10 border border-amber-400/20'"
          >
            <div class="text-sm">
              <div class="font-semibold" :class="config.llm_api_key ? 'text-emerald-300' : 'text-amber-300'">
                {{ config.llm_api_key ? '已配置' : '未配置' }}
              </div>
              <div class="text-xs text-slate-400 mt-0.5">{{ config.llm_model || '默认模型' }}</div>
            </div>
            <div class="text-xs text-slate-500">
              {{ config.llm_api_key ? 'LLM 预测' : '启发式兜底' }}
            </div>
          </div>

          <!-- Ollama 模型列表 -->
          <div v-if="isOllama" class="p-3 rounded-lg bg-white/5 border border-white/10">
            <div class="flex items-center justify-between mb-2">
              <span class="text-xs text-slate-400">选择模型（点击选用）</span>
              <button
                @click="loadOllamaModels"
                :disabled="loadingModels"
                class="text-xs text-violet-300 hover:text-violet-200"
              >
                {{ loadingModels ? '刷新中...' : '刷新本地列表' }}
              </button>
            </div>

            <!-- 云模型预设（无需下载） -->
            <div class="mb-2">
              <div class="text-[10px] text-slate-500 uppercase tracking-wider mb-1 flex items-center gap-1">
                <svg class="w-3 h-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M18 10h-1.26A8 8 0 1 0 9 20h9a5 5 0 0 0 0-10z"/>
                </svg>
                云模型（无需下载，订阅调用）
              </div>
              <div class="space-y-1 max-h-32 overflow-y-auto pr-1">
                <button
                  v-for="m in cloudPresets"
                  :key="m.name"
                  @click="selectModel(m.name)"
                  :class="[
                    'w-full flex items-center justify-between px-3 py-1.5 rounded-lg text-sm transition',
                    form.llm_model === m.name
                      ? 'bg-violet-500/20 text-violet-200 border border-violet-400/30'
                      : 'bg-white/5 text-slate-300 hover:bg-white/10 border border-transparent',
                  ]"
                >
                  <div class="flex items-center gap-2">
                    <span class="font-mono">{{ m.name }}</span>
                    <span class="px-1.5 py-0.5 rounded-full bg-sky-500/20 text-sky-300 text-[9px] font-bold">CLOUD</span>
                  </div>
                  <span class="text-[10px] text-slate-500">{{ m.desc }}</span>
                </button>
              </div>
            </div>

            <!-- 本地已安装模型 -->
            <div v-if="ollamaModels.length" class="mb-2">
              <div class="text-[10px] text-slate-500 uppercase tracking-wider mb-1">本地已安装</div>
              <div class="space-y-1 max-h-32 overflow-y-auto pr-1">
                <button
                  v-for="m in ollamaModels"
                  :key="m.name"
                  @click="selectModel(m.name)"
                  :class="[
                    'w-full flex items-center justify-between px-3 py-1.5 rounded-lg text-sm transition',
                    form.llm_model === m.name
                      ? 'bg-violet-500/20 text-violet-200 border border-violet-400/30'
                      : 'bg-white/5 text-slate-300 hover:bg-white/10 border border-transparent',
                  ]"
                >
                  <span class="font-mono">{{ m.name }}</span>
                  <span class="text-[10px] text-slate-500">{{ formatSize(m.size) }}</span>
                </button>
              </div>
            </div>
            <div v-else-if="!loadingModels" class="text-xs text-slate-500 py-1 text-center">
              本地暂无已安装模型（可使用上方云模型）
            </div>

            <!-- 拉取新模型 -->
            <div class="mt-2 pt-2 border-t border-white/10">
              <div class="text-xs text-slate-400 mb-1">拉取新模型（本地下载）</div>
              <div class="flex gap-2">
                <input
                  v-model="pullModelName"
                  type="text"
                  placeholder="如 qwen2.5:3b"
                  class="flex-1 bg-white/10 border border-white/20 rounded-lg px-3 py-1.5 text-sm text-slate-100 outline-none focus:border-violet-400"
                  @keyup.enter="pullModel"
                />
                <button
                  @click="pullModel"
                  :disabled="pulling || !pullModelName.trim()"
                  class="px-3 py-1.5 rounded-lg bg-violet-500 hover:bg-violet-600 text-white text-sm font-bold transition disabled:opacity-50"
                >
                  {{ pulling ? '拉取中' : '拉取' }}
                </button>
              </div>
              <!-- 拉取进度 -->
              <div v-if="pullStatus.status !== 'idle'" class="mt-2 p-2 rounded-lg bg-black/30 text-xs">
                <div :class="pullStatus.status === 'done' ? 'text-emerald-300' : pullStatus.status === 'error' ? 'text-red-300' : 'text-slate-300'">
                  <span v-if="pullStatus.status === 'pulling'">⏳ {{ pullStatus.progress }}</span>
                  <span v-else-if="pullStatus.status === 'done'">✓ 拉取完成</span>
                  <span v-else>✗ {{ pullStatus.progress }}</span>
                </div>
              </div>
            </div>
          </div>

          <!-- 表单 -->
          <div>
            <label class="block text-xs text-slate-400 mb-1">模型名称</label>
            <input
              v-model="form.llm_model"
              type="text"
              placeholder="如 glm-4.7:cloud / deepseek-ai/DeepSeek-R1"
              class="w-full bg-white/10 border border-white/20 rounded-lg px-3 py-2 text-sm text-slate-100 outline-none focus:border-violet-400"
            />
            <div class="text-[10px] text-slate-500 mt-1">留空则使用默认：{{ config.defaults?.llm_model }}</div>
          </div>

          <div>
            <label class="block text-xs text-slate-400 mb-1">Base URL</label>
            <input
              v-model="form.llm_base_url"
              type="text"
              placeholder="如 http://localhost:11434/v1"
              class="w-full bg-white/10 border border-white/20 rounded-lg px-3 py-2 text-sm text-slate-100 outline-none focus:border-violet-400"
            />
            <div class="text-[10px] text-slate-500 mt-1">Ollama 默认 http://localhost:11434/v1</div>
          </div>

          <div>
            <label class="block text-xs text-slate-400 mb-1">API Key</label>
            <input
              v-model="form.llm_api_key"
              type="password"
              placeholder="Ollama 填 ollama，云端填实际 Key"
              class="w-full bg-white/10 border border-white/20 rounded-lg px-3 py-2 text-sm text-slate-100 outline-none focus:border-violet-400"
            />
            <div class="text-[10px] text-slate-500 mt-1">已保存的 Key 不会回显，留空表示不修改</div>
          </div>

          <!-- 快捷预设 -->
          <div>
            <div class="text-xs text-slate-400 mb-2">快捷预设</div>
            <div class="grid grid-cols-2 gap-2">
              <button
                v-for="preset in presets"
                :key="preset.name"
                @click="applyPreset(preset)"
                class="px-3 py-2 rounded-lg bg-white/5 border border-white/10 text-xs text-slate-300 hover:bg-white/10 transition text-left"
              >
                <div class="font-semibold text-slate-200">{{ preset.name }}</div>
                <div class="text-[10px] text-slate-500 truncate">{{ preset.llm_model }}</div>
              </button>
            </div>
          </div>

          <!-- 测试结果 -->
          <div
            v-if="testResult"
            class="p-3 rounded-lg text-sm"
            :class="testResult.ok ? 'bg-emerald-500/10 border border-emerald-400/20 text-emerald-300' : 'bg-red-500/10 border border-red-400/20 text-red-300'"
          >
            <div v-if="testResult.ok">
              ✓ 连接成功 · {{ testResult.used_llm ? 'LLM' : '启发式' }}
              <span v-if="testResult.sample?.red_balls?.length">
                · 示例：{{ testResult.sample.red_balls.join(',') }} + {{ testResult.sample.blue_balls.join(',') }}
              </span>
            </div>
            <div v-else>✗ {{ testResult.error }}</div>
          </div>
        </div>

        <!-- 底部操作 -->
        <div class="flex items-center gap-2 px-5 py-4 border-t border-white/10 sticky bottom-0 bg-slate-900">
          <button
            @click="testConnection"
            :disabled="testing"
            class="px-4 py-2 rounded-lg bg-white/10 hover:bg-white/20 text-slate-200 text-sm font-bold transition disabled:opacity-50"
          >
            {{ testing ? '测试中...' : '测试连接' }}
          </button>
          <div class="flex-1" />
          <button
            @click="close"
            class="px-4 py-2 rounded-lg bg-white/10 hover:bg-white/20 text-slate-300 text-sm transition"
          >
            取消
          </button>
          <button
            @click="save"
            :disabled="saving"
            class="px-5 py-2 rounded-lg bg-violet-500 hover:bg-violet-600 text-white text-sm font-bold transition disabled:opacity-50"
          >
            {{ saving ? '保存中...' : '保存' }}
          </button>
        </div>
      </div>
    </div>
  </transition>
</template>

<script setup>
import { ref, watch, computed, onUnmounted } from 'vue'
import { api } from '../api.js'
import { useToast } from '../composables/useToast.js'

const toast = useToast()

const props = defineProps({
  visible: { type: Boolean, default: false },
})
const emit = defineEmits(['close', 'saved'])

const config = ref({ llm_api_key: '', llm_base_url: '', llm_model: '', defaults: {} })
const form = ref({ llm_api_key: '', llm_base_url: '', llm_model: '' })
const saving = ref(false)
const testing = ref(false)
const testResult = ref(null)

// Ollama 模型管理
const ollamaModels = ref([])
const loadingModels = ref(false)
const pullModelName = ref('')
const pulling = ref(false)
const pullStatus = ref({ status: 'idle', progress: '', log: [] })
let pullTimer = null

const isOllama = computed(() => {
  const url = form.value.llm_base_url || config.value.llm_base_url || ''
  return url.includes('localhost:11434') || url.includes('127.0.0.1:11434')
})

// Ollama 云模型预设（无需下载，通过订阅调用）
const cloudPresets = [
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

const presets = [
  { name: 'Ollama 本地', llm_model: 'glm-4.7:cloud', llm_base_url: 'http://localhost:11434/v1', llm_api_key: 'ollama' },
  { name: 'SiliconFlow', llm_model: 'deepseek-ai/DeepSeek-R1', llm_base_url: 'https://api.siliconflow.cn/v1', llm_api_key: '' },
  { name: 'DeepSeek 官方', llm_model: 'deepseek-chat', llm_base_url: 'https://api.deepseek.com/v1', llm_api_key: '' },
  { name: 'OpenAI', llm_model: 'gpt-4o-mini', llm_base_url: 'https://api.openai.com/v1', llm_api_key: '' },
]

async function loadConfig() {
  try {
    const r = await api.getLlmConfig()
    config.value = r
    form.value.llm_base_url = r.llm_base_url
    form.value.llm_model = r.llm_model
    form.value.llm_api_key = ''
    testResult.value = null
    // 如果是 Ollama，自动加载模型列表
    if (isOllama.value) loadOllamaModels()
  } catch (e) {
    toast.error('加载配置失败: ' + e.message)
  }
}

async function loadOllamaModels() {
  loadingModels.value = true
  try {
    const r = await api.getOllamaModels()
    if (r.ok) {
      ollamaModels.value = r.models
    } else {
      toast.error('获取模型列表失败: ' + r.error)
    }
  } catch (e) {
    toast.error('获取模型列表失败: ' + e.message)
  } finally {
    loadingModels.value = false
  }
}

function selectModel(name) {
  form.value.llm_model = name
}

async function pullModel() {
  const name = pullModelName.value.trim()
  if (!name) return
  pulling.value = true
  pullStatus.value = { status: 'pulling', progress: 'starting...', log: [] }
  try {
    await api.pullOllamaModel(name)
    toast.success(`开始拉取 ${name}`)
    // 轮询拉取状态
    pullTimer = setInterval(async () => {
      try {
        const r = await api.getPullStatus(name)
        pullStatus.value = r.status
        if (r.status.status === 'done' || r.status.status === 'error') {
          clearInterval(pullTimer)
          pullTimer = null
          pulling.value = false
          if (r.status.status === 'done') {
            toast.success(`${name} 拉取完成`)
            loadOllamaModels()
          } else {
            toast.error(`${name} 拉取失败: ${r.status.progress}`)
          }
        }
      } catch {}
    }, 2000)
  } catch (e) {
    toast.error('拉取失败: ' + e.message)
    pulling.value = false
    pullStatus.value = { status: 'error', progress: e.message, log: [] }
  }
}

function applyPreset(preset) {
  form.value.llm_model = preset.llm_model
  form.value.llm_base_url = preset.llm_base_url
  if (preset.llm_api_key) form.value.llm_api_key = preset.llm_api_key
  testResult.value = null
  if (isOllama.value) loadOllamaModels()
}

async function save() {
  saving.value = true
  try {
    await api.saveLlmConfig(form.value)
    toast.success('配置已保存')
    emit('saved')
    close()
  } catch (e) {
    toast.error('保存失败: ' + e.message)
  } finally {
    saving.value = false
  }
}

async function testConnection() {
  testing.value = true
  testResult.value = null
  try {
    if (form.value.llm_api_key || form.value.llm_model !== config.value.llm_model || form.value.llm_base_url !== config.value.llm_base_url) {
      await api.saveLlmConfig(form.value)
      await loadConfig()
    }
    testResult.value = await api.testLlmConnection()
  } catch (e) {
    testResult.value = { ok: false, error: e.message }
  } finally {
    testing.value = false
  }
}

function close() {
  if (pullTimer) {
    clearInterval(pullTimer)
    pullTimer = null
  }
  emit('close')
}

function formatSize(bytes) {
  if (!bytes) return ''
  if (bytes >= 1e9) return (bytes / 1e9).toFixed(1) + 'GB'
  if (bytes >= 1e6) return (bytes / 1e6).toFixed(0) + 'MB'
  return (bytes / 1e3).toFixed(0) + 'KB'
}

watch(
  () => props.visible,
  (v) => {
    if (v) loadConfig()
  },
)

onUnmounted(() => {
  if (pullTimer) clearInterval(pullTimer)
})
</script>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
