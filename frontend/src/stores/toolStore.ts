import { create } from 'zustand'

export type ActiveTool = 'navigate' | 'brush' | 'eraser'

interface ToolState {
  activeTool: ActiveTool
  brushSize: number
  activeLabel: number
  hasUnsavedEdits: boolean

  setTool: (tool: ActiveTool) => void
  setBrushSize: (size: number) => void
  setActiveLabel: (label: number) => void
  setUnsavedEdits: (value: boolean) => void
}

export const useToolStore = create<ToolState>((set) => ({
  activeTool: 'navigate',
  brushSize: 10,
  activeLabel: 1,
  hasUnsavedEdits: false,

  setTool: (tool) => set({ activeTool: tool }),
  setBrushSize: (size) => set({ brushSize: Math.max(1, Math.min(50, size)) }),
  setActiveLabel: (label) => set({ activeLabel: label }),
  setUnsavedEdits: (value) => set({ hasUnsavedEdits: value }),
}))
