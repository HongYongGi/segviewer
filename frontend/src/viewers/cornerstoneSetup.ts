import {
  init as csInit,
  RenderingEngine,
  Enums,
  volumeLoader,
  cache,
  setVolumesForViewports,
  type Types,
} from '@cornerstonejs/core'
import {
  init as csToolsInit,
  addTool,
  ToolGroupManager,
  WindowLevelTool,
  PanTool,
  ZoomTool,
  StackScrollTool,
  CrosshairsTool,
  AnnotationDisplayTool as SegmentationDisplayTool,
  BrushTool,
  Enums as csToolsEnums,
  segmentation,
} from '@cornerstonejs/tools'

let initialized = false

export async function initCornerstone(): Promise<void> {
  if (initialized) return
  await csInit()
  csToolsInit()

  addTool(WindowLevelTool)
  addTool(PanTool)
  addTool(ZoomTool)
  addTool(StackScrollTool)
  addTool(CrosshairsTool)
  addTool(SegmentationDisplayTool)
  addTool(BrushTool)

  initialized = true
}

export const RENDERING_ENGINE_ID = 'segviewer-engine'
export const TOOL_GROUP_ID = 'segviewer-tools'

export const VIEWPORT_IDS = {
  AXIAL: 'viewport-axial',
  CORONAL: 'viewport-coronal',
  SAGITTAL: 'viewport-sagittal',
  VOLUME_3D: 'viewport-3d',
} as const

export function createRenderingEngine(): RenderingEngine {
  return new RenderingEngine(RENDERING_ENGINE_ID)
}

export function setupToolGroup(): void {
  const existing = ToolGroupManager.getToolGroup(TOOL_GROUP_ID)
  if (existing) return

  const toolGroup = ToolGroupManager.createToolGroup(TOOL_GROUP_ID)
  if (!toolGroup) return

  toolGroup.addTool(WindowLevelTool.toolName)
  toolGroup.addTool(PanTool.toolName)
  toolGroup.addTool(ZoomTool.toolName)
  toolGroup.addTool(StackScrollTool.toolName)
  toolGroup.addTool(SegmentationDisplayTool.toolName)

  toolGroup.setToolActive(WindowLevelTool.toolName, {
    bindings: [{ mouseButton: csToolsEnums.MouseBindings.Primary }],
  })
  toolGroup.setToolActive(PanTool.toolName, {
    bindings: [{ mouseButton: csToolsEnums.MouseBindings.Secondary }],
  })
  toolGroup.setToolActive(ZoomTool.toolName, {
    bindings: [{ mouseButton: csToolsEnums.MouseBindings.Auxiliary }],
  })
  toolGroup.setToolActive(StackScrollTool.toolName, {
    bindings: [{ mouseButton: csToolsEnums.MouseBindings.Wheel as unknown as number }],
  })
  toolGroup.setToolEnabled(SegmentationDisplayTool.toolName)
}

export {
  RenderingEngine,
  Enums,
  volumeLoader,
  cache,
  setVolumesForViewports,
  ToolGroupManager,
  segmentation,
  csToolsEnums,
  BrushTool,
  SegmentationDisplayTool,
}
export type { Types }
