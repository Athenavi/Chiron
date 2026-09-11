import { afterEach, beforeEach, describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import { nextTick } from 'vue'
import ImageViewer from '../common/ImageViewer.vue'
import { closeImageViewer, openImageViewer, useImageViewer } from '../common/imageViewerState'

beforeEach(() => { closeImageViewer() })
afterEach(() => { closeImageViewer() })

/** Teleport 会把内容移出组件树，stub 掉它才能用 wrapper.find 断言 */
const mountViewer = () => mount(ImageViewer, { global: { stubs: { teleport: true } } })

describe('ImageViewer（图片查看器）', () => {
  it('未打开时不渲染任何东西', () => {
    expect(mountViewer().find('.viewer-mask').exists()).toBe(false)
  })

  it('打开后渲染遮罩、图片与工具条', async () => {
    const wrapper = mountViewer()
    openImageViewer({ src: '/v1/media/a.png', alt: '示意图' })
    await nextTick()

    expect(wrapper.find('.viewer-mask').exists()).toBe(true)
    expect(wrapper.find('.viewer-img').attributes('src')).toBe('/v1/media/a.png')
    expect(wrapper.text()).toContain('示意图')
    expect(wrapper.find('.viewer-percent').text()).toBe('100%')
  })

  it('放大后百分比变化，1:1 恢复原始大小', async () => {
    const wrapper = mountViewer()
    openImageViewer({ src: '/x.png' })
    await nextTick()

    await wrapper.find('[title="放大（+）"]').trigger('click')
    expect(wrapper.find('.viewer-percent').text()).toBe('125%')
    await wrapper.find('[title="原始大小（0）"]').trigger('click')
    expect(wrapper.find('.viewer-percent').text()).toBe('100%')
  })

  it('提供新标签打开与下载链接', async () => {
    const wrapper = mountViewer()
    openImageViewer({ src: '/v1/media/a.png', alt: '示意图' })
    await nextTick()

    const links = wrapper.findAll('a')
    expect(links.map(link => link.attributes('href'))).toEqual(['/v1/media/a.png', '/v1/media/a.png'])
    expect(links[0]!.attributes('target')).toBe('_blank')
    expect(links[0]!.attributes('rel')).toContain('noopener')
    expect(links[1]!.attributes('download')).toBe('示意图')
  })

  it('Esc 关闭，点击遮罩也关闭', async () => {
    const wrapper = mountViewer()
    openImageViewer({ src: '/x.png' })
    await nextTick()

    window.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }))
    await nextTick()
    expect(useImageViewer().current.value).toBeNull()

    openImageViewer({ src: '/x.png' })
    await nextTick()
    await wrapper.find('.viewer-mask').trigger('click')
    await nextTick()
    expect(useImageViewer().current.value).toBeNull()
  })

  it('换图时缩放重置为原始大小', async () => {
    const wrapper = mountViewer()
    openImageViewer({ src: '/a.png' })
    await nextTick()
    await wrapper.find('[title="放大（+）"]').trigger('click')
    expect(wrapper.find('.viewer-percent').text()).toBe('125%')

    openImageViewer({ src: '/b.png' })
    await nextTick()
    expect(wrapper.find('.viewer-percent').text()).toBe('100%')
  })

  it('空 src 不打开（避免露出空遮罩）', async () => {
    mountViewer()
    openImageViewer({ src: '' })
    await nextTick()
    expect(useImageViewer().current.value).toBeNull()
  })
})
