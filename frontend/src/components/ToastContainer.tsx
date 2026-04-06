import { useToastStore } from '../stores/toastStore'

const TOAST_STYLES = {
  success: 'bg-[#4ecca3]/90 text-white',
  error: 'bg-[#e94560]/90 text-white',
  warning: 'bg-[#f0a500]/90 text-black',
  info: 'bg-[#0f3460]/90 text-white',
}

const TOAST_ICONS = {
  success: '\u2713',
  error: '\u2717',
  warning: '\u26A0',
  info: '\u2139',
}

export default function ToastContainer() {
  const { toasts, removeToast } = useToastStore()

  if (toasts.length === 0) return null

  return (
    <div className="fixed right-4 top-4 z-50 flex flex-col gap-2">
      {toasts.map((toast) => (
        <div
          key={toast.id}
          className={`flex items-center gap-2 rounded-lg px-4 py-3 shadow-lg transition-all duration-300 ${TOAST_STYLES[toast.type]}`}
          style={{ minWidth: '280px', maxWidth: '420px' }}
        >
          <span className="text-lg">{TOAST_ICONS[toast.type]}</span>
          <span className="flex-1 text-sm">{toast.message}</span>
          <button
            onClick={() => removeToast(toast.id)}
            className="ml-2 opacity-70 hover:opacity-100"
          >
            x
          </button>
        </div>
      ))}
    </div>
  )
}
