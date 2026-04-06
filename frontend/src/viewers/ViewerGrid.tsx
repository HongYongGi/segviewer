import { useEffect, useRef, useState } from 'react'
import { useImageStore } from '../stores/imageStore'
import {
  initCornerstone,
  createRenderingEngine,
  setupToolGroup,
  RENDERING_ENGINE_ID,
  TOOL_GROUP_ID,
  VIEWPORT_IDS,
  Enums,
  RenderingEngine,
  ToolGroupManager,
  setVolumesForViewports,
  volumeLoader,
  cache,
} from './cornerstoneSetup'

interface ViewerGridProps {
  windowWidth: number
  windowLevel: number
}

const VOLUME_ID = 'segviewer-ct-volume'

export default function ViewerGrid({ windowWidth, windowLevel }: ViewerGridProps) {
  const axialRef = useRef<HTMLDivElement>(null)
  const coronalRef = useRef<HTMLDivElement>(null)
  const sagittalRef = useRef<HTMLDivElement>(null)
  const vol3dRef = useRef<HTMLDivElement>(null)
  const engineRef = useRef<RenderingEngine | null>(null)
  const [ready, setReady] = useState(false)

  const { volumeData, volumeHeaders } = useImageStore()

  useEffect(() => {
    let cancelled = false

    const setup = async () => {
      await initCornerstone()
      if (cancelled) return

      const engine = createRenderingEngine()
      engineRef.current = engine
      setupToolGroup()

      const viewports = [
        {
          viewportId: VIEWPORT_IDS.AXIAL,
          type: Enums.ViewportType.ORTHOGRAPHIC,
          element: axialRef.current!,
          defaultOptions: { orientation: Enums.OrientationAxis.AXIAL },
        },
        {
          viewportId: VIEWPORT_IDS.CORONAL,
          type: Enums.ViewportType.ORTHOGRAPHIC,
          element: coronalRef.current!,
          defaultOptions: { orientation: Enums.OrientationAxis.CORONAL },
        },
        {
          viewportId: VIEWPORT_IDS.SAGITTAL,
          type: Enums.ViewportType.ORTHOGRAPHIC,
          element: sagittalRef.current!,
          defaultOptions: { orientation: Enums.OrientationAxis.SAGITTAL },
        },
      ]

      engine.setViewports(viewports)

      const toolGroup = ToolGroupManager.getToolGroup(TOOL_GROUP_ID)
      if (toolGroup) {
        toolGroup.addViewport(VIEWPORT_IDS.AXIAL, RENDERING_ENGINE_ID)
        toolGroup.addViewport(VIEWPORT_IDS.CORONAL, RENDERING_ENGINE_ID)
        toolGroup.addViewport(VIEWPORT_IDS.SAGITTAL, RENDERING_ENGINE_ID)
      }

      setReady(true)
    }

    setup()

    return () => {
      cancelled = true
      if (engineRef.current) {
        engineRef.current.destroy()
        engineRef.current = null
      }
    }
  }, [])

  useEffect(() => {
    if (!ready || !volumeData || !volumeHeaders || !engineRef.current) return

    const shapeStr = volumeHeaders['x-image-shape'] || ''
    const spacingStr = volumeHeaders['x-image-spacing'] || ''
    const affineStr = volumeHeaders['x-image-affine'] || ''

    const shape = shapeStr.split(',').map(Number) as [number, number, number]
    const spacing = spacingStr.split(',').map(Number) as [number, number, number]

    let direction = new Float32Array([1, 0, 0, 0, 1, 0, 0, 0, 1])
    let origin: [number, number, number] = [0, 0, 0]

    if (affineStr) {
      const affine = affineStr.split(',').map(Number)
      if (affine.length === 16) {
        direction = new Float32Array([
          affine[0] / spacing[0], affine[1] / spacing[1], affine[2] / spacing[2],
          affine[4] / spacing[0], affine[5] / spacing[1], affine[6] / spacing[2],
          affine[8] / spacing[0], affine[9] / spacing[1], affine[10] / spacing[2],
        ])
        origin = [affine[3], affine[7], affine[11]]
      }
    }

    loadVolume(shape, spacing, direction, origin)
  }, [ready, volumeData, volumeHeaders])

  useEffect(() => {
    if (!ready || !engineRef.current) return
    const engine = engineRef.current

    for (const vpId of [VIEWPORT_IDS.AXIAL, VIEWPORT_IDS.CORONAL, VIEWPORT_IDS.SAGITTAL]) {
      const vp = engine.getViewport(vpId)
      if (vp && 'setVOI' in vp) {
        (vp as unknown as { setVOI: (range: { lower: number; upper: number }) => void }).setVOI({
          lower: windowLevel - windowWidth / 2,
          upper: windowLevel + windowWidth / 2,
        })
        vp.render()
      }
    }
  }, [windowWidth, windowLevel, ready])

  const loadVolume = async (
    shape: [number, number, number],
    spacing: [number, number, number],
    direction: Float32Array,
    origin: [number, number, number],
  ) => {
    const engine = engineRef.current
    if (!engine || !volumeData) return

    try {
      cache.removeVolumeLoadObject(VOLUME_ID)
    } catch { /* ignore */ }

    try {
      const volume = await volumeLoader.createAndCacheVolume(VOLUME_ID, {
        imageIds: [],
      })

      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const vol = volume as any
      vol.dimensions = shape
      vol.spacing = spacing
      vol.direction = direction
      vol.origin = origin

      if (vol.voxelManager && typeof vol.voxelManager.getScalarData === 'function') {
        const scalarData = vol.voxelManager.getScalarData() as Float32Array
        if (scalarData.length === volumeData.length) {
          scalarData.set(volumeData)
        }
      }

      await setVolumesForViewports(
        engine,
        [{ volumeId: VOLUME_ID }],
        [VIEWPORT_IDS.AXIAL, VIEWPORT_IDS.CORONAL, VIEWPORT_IDS.SAGITTAL],
      )

      engine.renderViewports([VIEWPORT_IDS.AXIAL, VIEWPORT_IDS.CORONAL, VIEWPORT_IDS.SAGITTAL])
    } catch (err) {
      console.error('Failed to load volume:', err)
    }
  }

  return (
    <div className="grid flex-1 grid-cols-2 grid-rows-2 gap-px bg-[#0f3460]">
      <div ref={axialRef} className="relative bg-black">
        {!volumeData && <PlaceholderLabel label="Axial" />}
        <ViewportLabel label="Axial" />
      </div>
      <div ref={coronalRef} className="relative bg-black">
        {!volumeData && <PlaceholderLabel label="Coronal" />}
        <ViewportLabel label="Coronal" />
      </div>
      <div ref={sagittalRef} className="relative bg-black">
        {!volumeData && <PlaceholderLabel label="Sagittal" />}
        <ViewportLabel label="Sagittal" />
      </div>
      <div ref={vol3dRef} className="relative flex items-center justify-center bg-black">
        <span className="text-sm text-[#e0e0e0]/20">3D View (Phase 2)</span>
      </div>
    </div>
  )
}

function PlaceholderLabel({ label }: { label: string }) {
  return (
    <div className="absolute inset-0 flex items-center justify-center">
      <span className="text-sm text-[#e0e0e0]/20">{label}</span>
    </div>
  )
}

function ViewportLabel({ label }: { label: string }) {
  return (
    <span className="pointer-events-none absolute left-2 top-1 font-mono text-xs text-white/60">
      {label}
    </span>
  )
}
