/** Toast 通知 composable。 */
import { ref } from 'vue'

const instance = ref(null)

export function setToastInstance(inst) {
  instance.value = inst
}

export function useToast() {
  const show = (message, type = 'info') => {
    if (instance.value) {
      instance.value.show(message, type)
    }
  }
  return {
    show,
    success: (msg) => show(msg, 'success'),
    error: (msg) => show(msg, 'error'),
    info: (msg) => show(msg, 'info'),
  }
}
