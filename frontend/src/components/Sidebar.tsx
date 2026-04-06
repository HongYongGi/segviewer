import { useImageStore } from '../stores/imageStore'
import { useSegmentationStore } from '../stores/segmentationStore'
import { formatBytes, formatPercent } from '../utils/colormap'

export default function Sidebar() {
  return (
    <aside className="flex w-[300px] shrink-0 flex-col overflow-y-auto border-l border-[#0f3460] bg-[#16213e]">
      <LabelPanel />
      <MetadataPanel />
    </aside>
  )
}

function LabelPanel() {
  const { labels, opacity, toggleVisibility, setOpacity, resultId } = useSegmentationStore()

  return (
    <div className="border-b border-[#0f3460] p-3">
      <h2 className="mb-2 text-sm font-semibold">Labels</h2>
      {!resultId ? (
        <p className="text-xs text-[#e0e0e0]/40">
          Upload an image and run inference to see labels.
        </p>
      ) : (
        <>
          <div className="mb-2 space-y-1">
            {labels.map((l) => (
              <label key={l.id} className="flex cursor-pointer items-center gap-2 text-xs">
                <input
                  type="checkbox"
                  checked={l.visible}
                  onChange={() => toggleVisibility(l.id)}
                  className="h-3 w-3"
                />
                <span
                  className="inline-block h-3 w-3 rounded-sm"
                  style={{ backgroundColor: `rgb(${l.color.join(',')})` }}
                />
                <span className="flex-1 truncate">{l.name}</span>
                <span className="text-[#e0e0e0]/40">
                  {formatPercent(l.voxelPercent)}
                </span>
              </label>
            ))}
          </div>
          <div className="flex items-center gap-2 text-xs">
            <span>Opacity</span>
            <input
              type="range"
              min={0}
              max={100}
              value={opacity}
              onChange={(e) => setOpacity(Number(e.target.value))}
              className="flex-1"
            />
            <span className="w-8 text-right">{opacity}%</span>
          </div>
        </>
      )}
    </div>
  )
}

function MetadataPanel() {
  const metadata = useImageStore((s) => s.metadata)

  return (
    <div className="p-3">
      <h2 className="mb-2 text-sm font-semibold">Metadata</h2>
      {!metadata ? (
        <p className="text-xs text-[#e0e0e0]/40">No image loaded.</p>
      ) : (
        <dl className="space-y-1 text-xs">
          <Row label="File" value={metadata.filename} />
          <Row label="Shape" value={metadata.shape.join(' x ')} />
          <Row label="Spacing" value={metadata.spacing.map((s) => `${s.toFixed(2)}`).join(' x ') + ' mm'} />
          <Row label="Orientation" value={metadata.orientation} />
          <Row label="Type" value={metadata.dtype} />
          <Row label="HU Range" value={`${metadata.hu_range[0]} ~ ${metadata.hu_range[1]}`} />
          <Row label="Size" value={formatBytes(metadata.file_size_bytes)} />
        </dl>
      )}
    </div>
  )
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between">
      <dt className="text-[#e0e0e0]/50">{label}</dt>
      <dd className="font-mono">{value}</dd>
    </div>
  )
}
