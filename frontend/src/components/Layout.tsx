interface LayoutProps {
  backendStatus: string
}

export default function Layout({ backendStatus }: LayoutProps) {
  return (
    <div className="flex h-screen w-screen flex-col bg-[#1a1a2e] text-[#e0e0e0]">
      {/* Toolbar */}
      <header className="flex h-12 shrink-0 items-center gap-4 border-b border-[#0f3460] bg-[#16213e] px-4">
        <h1 className="text-lg font-bold tracking-wide">SegViewer</h1>
        <button className="rounded bg-[#533483] px-3 py-1 text-sm hover:bg-[#533483]/80">
          Upload NIfTI
        </button>
        <select className="rounded border border-[#0f3460] bg-[#1a1a2e] px-2 py-1 text-sm">
          <option>Model: (none)</option>
        </select>
        <button
          className="rounded bg-[#533483] px-3 py-1 text-sm opacity-50"
          disabled
        >
          Run Inference
        </button>
        <div className="flex-1" />
        <span className="text-xs text-[#e0e0e0]/50">v0.1.0</span>
      </header>

      {/* Main content: 2x2 grid + sidebar */}
      <div className="flex flex-1 overflow-hidden">
        {/* Viewport grid */}
        <div className="grid flex-1 grid-cols-2 grid-rows-2 gap-px bg-[#0f3460]">
          <ViewportPlaceholder label="Axial" />
          <ViewportPlaceholder label="Coronal" />
          <ViewportPlaceholder label="Sagittal" />
          <ViewportPlaceholder label="3D View" />
        </div>

        {/* Sidebar */}
        <aside className="flex w-[300px] shrink-0 flex-col border-l border-[#0f3460] bg-[#16213e]">
          <div className="border-b border-[#0f3460] p-3">
            <h2 className="mb-2 text-sm font-semibold">Labels</h2>
            <p className="text-xs text-[#e0e0e0]/40">
              Upload an image and run inference to see labels.
            </p>
          </div>
          <div className="p-3">
            <h2 className="mb-2 text-sm font-semibold">Metadata</h2>
            <p className="text-xs text-[#e0e0e0]/40">No image loaded.</p>
          </div>
        </aside>
      </div>

      {/* Status bar */}
      <footer className="flex h-6 shrink-0 items-center gap-4 border-t border-[#0f3460] bg-[#16213e] px-4 text-xs text-[#e0e0e0]/50">
        <span>
          Backend:{' '}
          <span
            className={
              backendStatus === 'ok' ? 'text-[#4ecca3]' : 'text-[#e94560]'
            }
          >
            {backendStatus}
          </span>
        </span>
        <span>GPU: N/A</span>
        <span>Status: Ready</span>
      </footer>
    </div>
  )
}

function ViewportPlaceholder({ label }: { label: string }) {
  return (
    <div className="flex items-center justify-center bg-black">
      <span className="text-sm text-[#e0e0e0]/20">{label}</span>
    </div>
  )
}
