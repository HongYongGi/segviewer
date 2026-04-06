import { create } from 'zustand'
import type { ImageMetadata } from '../types/image'
import apiClient from '../api/client'

interface ImageState {
  imageId: string | null
  metadata: ImageMetadata | null
  uploading: boolean
  uploadProgress: number
  volumeData: Float32Array | null
  volumeHeaders: Record<string, string>
  loading: boolean

  upload: (file: File) => Promise<void>
  loadVolume: (imageId: string) => Promise<void>
  reset: () => void
}

export const useImageStore = create<ImageState>((set, get) => ({
  imageId: null,
  metadata: null,
  uploading: false,
  uploadProgress: 0,
  volumeData: null,
  volumeHeaders: {},
  loading: false,

  upload: async (file: File) => {
    set({ uploading: true, uploadProgress: 0 })
    try {
      const formData = new FormData()
      formData.append('file', file)
      const res = await apiClient.post('/images/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        onUploadProgress: (e) => {
          if (e.total) set({ uploadProgress: Math.round((e.loaded / e.total) * 100) })
        },
      })
      set({
        imageId: res.data.image_id,
        metadata: res.data.metadata,
        uploading: false,
        uploadProgress: 100,
      })
      await get().loadVolume(res.data.image_id)
    } catch {
      set({ uploading: false, uploadProgress: 0 })
      throw new Error('Upload failed')
    }
  },

  loadVolume: async (imageId: string) => {
    set({ loading: true })
    try {
      const res = await apiClient.get(`/images/${imageId}/volume`, {
        responseType: 'arraybuffer',
      })
      const headers: Record<string, string> = {}
      for (const key of ['x-image-shape', 'x-image-dtype', 'x-image-spacing', 'x-image-byteorder', 'x-image-affine']) {
        const v = res.headers[key]
        if (v) headers[key] = v
      }
      set({
        volumeData: new Float32Array(res.data),
        volumeHeaders: headers,
        loading: false,
      })
    } catch {
      set({ loading: false })
    }
  },

  reset: () =>
    set({
      imageId: null,
      metadata: null,
      uploading: false,
      uploadProgress: 0,
      volumeData: null,
      volumeHeaders: {},
      loading: false,
    }),
}))
