import { useEffect, useState } from 'react'
import Toolbar from './components/Toolbar'
import Sidebar from './components/Sidebar'
import ViewerGrid from './viewers/ViewerGrid'
import ToastContainer from './components/ToastContainer'

interface GpuInfo {
  gpu_name: string
  vram_used_mb: number
  vram_total_mb: number
  cuda_available: boolean
}

function App() {
  const [backendStatus, setBackendStatus] = useState<string>('connecting...')
  const [gpuInfo, setGpuInfo] = useState<GpuInfo | null>(null)
  const [windowWidth, setWindowWidth] = useState(400)
  const [windowLevel, setWindowLevel] = useState(40)

  useEffect(() => {
    fetch('/api/health')
      .then((res) => res.json())
      .then((data) => setBackendStatus(data.status))
      .catch(() => setBackendStatus('offline'))

    fetch('/api/system/gpu')
      .then((res) => res.json())
      .then((data) => setGpuInfo(data))
      .catch(() => {})
  }, [])

  const handleWLChange = (w: number, l: number) => {
    setWindowWidth(w)
    setWindowLevel(l)
  }

  const gpuText = gpuInfo
    ? gpuInfo.cuda_available
      ? `${gpuInfo.gpu_name} (${gpuInfo.vram_used_mb}/${gpuInfo.vram_total_mb}MB)`
      : 'CPU only'
    : 'N/A'

  return (
    <div className="flex h-screen w-screen flex-col bg-[#1a1a2e] text-[#e0e0e0]">
      <ToastContainer />
      <Toolbar onWLChange={handleWLChange} />

      <div className="flex flex-1 overflow-hidden">
        <ViewerGrid windowWidth={windowWidth} windowLevel={windowLevel} />
        <Sidebar />
      </div>

      <footer className="flex h-6 shrink-0 items-center gap-4 border-t border-[#0f3460] bg-[#16213e] px-4 text-xs text-[#e0e0e0]/50">
        <span>
          Backend:{' '}
          <span className={backendStatus === 'ok' ? 'text-[#4ecca3]' : 'text-[#e94560]'}>
            {backendStatus}
          </span>
        </span>
        <span>GPU: {gpuText}</span>
        <span>Status: Ready</span>
      </footer>
    </div>
  )
}

export default App
