export interface EditAction {
  sliceAxis: 'axial' | 'coronal' | 'sagittal'
  sliceIndex: number
  changedVoxels: {
    index: number
    oldValue: number
    newValue: number
  }[]
  timestamp: number
}

const MAX_HISTORY = 20

class UndoManager {
  private undoStack: EditAction[] = []
  private redoStack: EditAction[] = []
  private listeners: Array<() => void> = []

  push(action: EditAction): void {
    this.undoStack.push(action)
    if (this.undoStack.length > MAX_HISTORY) {
      this.undoStack.shift()
    }
    this.redoStack = []
    this.notify()
  }

  undo(applyFn: (voxels: { index: number; value: number }[]) => void): boolean {
    const action = this.undoStack.pop()
    if (!action) return false

    const restoreVoxels = action.changedVoxels.map((v) => ({
      index: v.index,
      value: v.oldValue,
    }))
    applyFn(restoreVoxels)

    this.redoStack.push(action)
    this.notify()
    return true
  }

  redo(applyFn: (voxels: { index: number; value: number }[]) => void): boolean {
    const action = this.redoStack.pop()
    if (!action) return false

    const applyVoxels = action.changedVoxels.map((v) => ({
      index: v.index,
      value: v.newValue,
    }))
    applyFn(applyVoxels)

    this.undoStack.push(action)
    this.notify()
    return true
  }

  get canUndo(): boolean {
    return this.undoStack.length > 0
  }

  get canRedo(): boolean {
    return this.redoStack.length > 0
  }

  get undoCount(): number {
    return this.undoStack.length
  }

  get redoCount(): number {
    return this.redoStack.length
  }

  clear(): void {
    this.undoStack = []
    this.redoStack = []
    this.notify()
  }

  subscribe(listener: () => void): () => void {
    this.listeners.push(listener)
    return () => {
      this.listeners = this.listeners.filter((l) => l !== listener)
    }
  }

  private notify(): void {
    for (const l of this.listeners) l()
  }
}

export const undoManager = new UndoManager()
