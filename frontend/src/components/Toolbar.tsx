import { useRef } from 'react'
import { useImageStore } from '../stores/imageStore'
import { useModelStore } from '../stores/modelStore'
import { useInferenceStore } from '../stores/inferenceStore'
import { useSegmentationStore } from '../stores/segmentationStore'

const WL_PRESETS = [
  { name: 'Abdomen', width: 400, level: 40 },
  { name: 'Lung', width: 1500, level: -600 },
  { name: 'Bone', width: 2000, level: 400 },
  { name: 'Brain', width: 80, level: 40 },
  { name: 'Liver', width: 150, level: 60 },
  { name: 'Mediastinum', width: 350, level: 50 },
] as const

interface ToolbarProps {
  onWLChange: (width: number, level: number) => void
}

export default function Toolbar({ onWLChange }: ToolbarProps) {
  const fileRef = useRef<HTMLInputElement>(null)
  const { upload, uploading, uploadProgress, imageId } = useImageStore()
  const { models, selectedDataset, selectedConfig, selectDataset, fetchModels } = useModelStore()
  const { runInference, running } = useInferenceStore()
  const loadSeg = useSegmentationStore((s) => s.loadSegmentation)

  const handleFile = async (file: File) => {
    await upload(file)
    await fetchModels()
  }

  const handleRunInference = async () => {
    if (!imageId || !selectedDataset || !selectedConfig) return
    await runInference({
      image_id: imageId,
      dataset_id: selectedDataset.dataset_id,
      dataset_name: selectedDataset.dataset_name,
      full_dataset_name: selectedDataset.full_dataset_name,
      trainer: selectedConfig.trainer,
      plans: selectedConfig.plans,
      configuration: selectedConfig.configuration,
      folds: selectedConfig.available_folds,
      labels: selectedConfig.labels,
    })

    const checkResult = () => {
      const s = useInferenceStore.getState().status
      if (s?.status === 'completed' && s.result_id) {
        loadSeg(s.result_id)
      } else if (s?.status !== 'completed' && s?.status !== 'failed') {
        setTimeout(checkResult, 500)
      }
    }
    setTimeout(checkResult, 1000)
  }

  return (
    <header className="flex h-12 shrink-0 items-center gap-3 border-b border-[#0f3460] bg-[#16213e] px-4">
      <h1 className="text-lg font-bold tracking-wide">SegViewer</h1>

      <input
        ref={fileRef}
        type="file"
        accept=".nii,.nii.gz"
        className="hidden"
        onChange={(e) => e.target.files?.[0] && handleFile(e.target.files[0])}
      />
      <button
        className="rounded bg-[#533483] px-3 py-1 text-sm hover:bg-[#533483]/80 disabled:opacity-50"
        disabled={uploading}
        onClick={() => fileRef.current?.click()}
      >
        {uploading ? `Uploading ${uploadProgress}%` : 'Upload NIfTI'}
      </button>

      {/* W/L preset */}
      <select
        className="rounded border border-[#0f3460] bg-[#1a1a2e] px-2 py-1 text-sm"
        onChange={(e) => {
          const p = WL_PRESETS.find((p) => p.name === e.target.value)
          if (p) onWLChange(p.width, p.level)
        }}
        defaultValue="Abdomen"
      >
        {WL_PRESETS.map((p) => (
          <option key={p.name} value={p.name}>
            {p.name} (W:{p.width} L:{p.level})
          </option>
        ))}
      </select>

      {/* Model selector */}
      <select
        className="rounded border border-[#0f3460] bg-[#1a1a2e] px-2 py-1 text-sm"
        value={selectedDataset?.full_dataset_name ?? ''}
        onChange={(e) => {
          const m = models.find((m) => m.full_dataset_name === e.target.value)
          selectDataset(m ?? null)
        }}
      >
        <option value="">Model: (none)</option>
        {models.map((m) => (
          <option key={m.full_dataset_name} value={m.full_dataset_name}>
            {m.dataset_id} - {m.dataset_name}
            {m.configurations[0] ? ` (${m.configurations[0].configuration})` : ''}
          </option>
        ))}
      </select>

      <button
        className="rounded bg-[#533483] px-3 py-1 text-sm hover:bg-[#533483]/80 disabled:opacity-50"
        disabled={!imageId || !selectedConfig || running}
        onClick={handleRunInference}
      >
        {running ? 'Running...' : 'Run Inference'}
      </button>

      <div className="flex-1" />

      {/* Inference progress */}
      {running && (
        <InferenceProgress />
      )}

      <span className="text-xs text-[#e0e0e0]/50">v0.1.0</span>
    </header>
  )
}

function InferenceProgress() {
  const status = useInferenceStore((s) => s.status)
  if (!status) return null
  return (
    <div className="flex items-center gap-2 text-xs">
      <div className="h-1.5 w-32 rounded-full bg-[#0f3460]">
        <div
          className="h-full rounded-full bg-[#4ecca3] transition-all"
          style={{ width: `${Math.max(0, status.progress)}%` }}
        />
      </div>
      <span className="text-[#e0e0e0]/70">
        {status.stage_detail || status.stage} ({status.progress}%)
      </span>
    </div>
  )
}
