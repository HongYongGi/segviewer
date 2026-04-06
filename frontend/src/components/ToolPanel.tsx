import { useEffect, useSyncExternalStore } from 'react'
import { useToolStore } from '../stores/toolStore'
import { useSegmentationStore } from '../stores/segmentationStore'
import { undoManager } from '../editors/UndoManager'
import apiClient from '../api/client'

export default function ToolPanel() {
  const { activeTool, brushSize, activeLabel, hasUnsavedEdits, setTool, setBrushSize, setActiveLabel, setUnsavedEdits } = useToolStore()
  const { labels, resultId, segData } = useSegmentationStore()
  const canUndo = useSyncExternalStore(
    (cb) => undoManager.subscribe(cb),
    () => undoManager.canUndo,
  )
  const canRedo = useSyncExternalStore(
    (cb) => undoManager.subscribe(cb),
    () => undoManager.canRedo,
  )

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLSelectElement) return

      switch (e.key.toLowerCase()) {
        case 'b': setTool('brush'); break
        case 'e': setTool('eraser'); break
        case 'n': case 'Escape': setTool('navigate'); break
        case '[': setBrushSize(brushSize - (e.shiftKey ? 5 : 1)); break
        case ']': setBrushSize(brushSize + (e.shiftKey ? 5 : 1)); break
        case 'z':
          if (e.ctrlKey || e.metaKey) {
            e.preventDefault()
            if (e.shiftKey) undoManager.redo(() => {})
            else undoManager.undo(() => {})
          }
          break
        case 's':
          if (e.ctrlKey || e.metaKey) {
            e.preventDefault()
            handleSave()
          }
          break
        default:
          if (/^[1-9]$/.test(e.key)) {
            const idx = parseInt(e.key)
            const label = labels.find((l) => l.id === idx)
            if (label) setActiveLabel(label.id)
          }
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [brushSize, labels])

  useEffect(() => {
    if (!hasUnsavedEdits) return
    const handler = (e: BeforeUnloadEvent) => {
      e.preventDefault()
    }
    window.addEventListener('beforeunload', handler)
    return () => window.removeEventListener('beforeunload', handler)
  }, [hasUnsavedEdits])

  const handleSave = async () => {
    if (!resultId || !segData) return
    const meta = useSegmentationStore.getState().metadata
    if (!meta) return

    try {
      await apiClient.put(`/segments/${resultId}`, segData.buffer, {
        headers: {
          'Content-Type': 'application/octet-stream',
          'X-Seg-Shape': meta.shape.join(','),
          'X-Seg-Dtype': 'uint8',
        },
      })
      setUnsavedEdits(false)
    } catch (err) {
      console.error('Save failed:', err)
    }
  }

  if (!resultId) return null

  return (
    <div className="border-b border-[#0f3460] p-3">
      <h2 className="mb-2 text-sm font-semibold">Tools</h2>

      <div className="mb-2 flex gap-1">
        {(['navigate', 'brush', 'eraser'] as const).map((tool) => (
          <button
            key={tool}
            className={`rounded px-2 py-1 text-xs ${
              activeTool === tool
                ? 'bg-[#533483] text-white'
                : 'bg-[#1a1a2e] text-[#e0e0e0]/70 hover:bg-[#0f3460]'
            }`}
            onClick={() => setTool(tool)}
          >
            {tool === 'navigate' ? 'Nav (N)' : tool === 'brush' ? 'Brush (B)' : 'Eraser (E)'}
          </button>
        ))}
      </div>

      {(activeTool === 'brush' || activeTool === 'eraser') && (
        <>
          <div className="mb-2 flex items-center gap-2 text-xs">
            <span>Size</span>
            <input
              type="range"
              min={1}
              max={50}
              value={brushSize}
              onChange={(e) => setBrushSize(Number(e.target.value))}
              className="flex-1"
            />
            <span className="w-6 text-right">{brushSize}</span>
          </div>

          {activeTool === 'brush' && (
            <div className="mb-2 text-xs">
              <span className="text-[#e0e0e0]/50">Active: </span>
              <span>{labels.find((l) => l.id === activeLabel)?.name ?? `Label ${activeLabel}`}</span>
            </div>
          )}
        </>
      )}

      <div className="flex gap-1">
        <button
          className="rounded bg-[#1a1a2e] px-2 py-1 text-xs disabled:opacity-30"
          disabled={!canUndo}
          onClick={() => undoManager.undo(() => {})}
          title="Ctrl+Z"
        >
          Undo
        </button>
        <button
          className="rounded bg-[#1a1a2e] px-2 py-1 text-xs disabled:opacity-30"
          disabled={!canRedo}
          onClick={() => undoManager.redo(() => {})}
          title="Ctrl+Shift+Z"
        >
          Redo
        </button>
        <div className="flex-1" />
        <button
          className={`rounded px-2 py-1 text-xs ${
            hasUnsavedEdits ? 'bg-[#4ecca3] text-black' : 'bg-[#1a1a2e] opacity-50'
          }`}
          disabled={!hasUnsavedEdits}
          onClick={handleSave}
          title="Ctrl+S"
        >
          Save
        </button>
      </div>
    </div>
  )
}
