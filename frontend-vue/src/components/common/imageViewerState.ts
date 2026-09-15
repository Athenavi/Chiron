/**
 * 图片查看器的全局状态。
 *
 * 为什么用模块级状态而不是 props 逐层传：图片散落在消息气泡、markdown 正文、
 * 工具结果里，任何一处都应该能唤起同一个查看器；逐层透传会让每个新增的图片位置
 * 都得记得接一遍事件。查看器本身在 App 上挂一个实例即可。
 */

import { ref } from 'vue'

export interface ViewerImage {
  src: string
  alt?: string
}

const current = ref<ViewerImage | null>(null)

export function openImageViewer(image: ViewerImage): void {
  if (!image.src) return
  current.value = image
}

export function closeImageViewer(): void {
  current.value = null
}

export function useImageViewer() {
  return { current, openImageViewer, closeImageViewer }
}
