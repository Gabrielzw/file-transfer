import { onBeforeUnmount, ref } from 'vue'

type Options = {
  onError: (message: string) => void
}

type Result = {
  triggerDownload: (url: string) => void
}

export function useIframeDownload(options: Options): Result {
  const downloadFrame = ref<HTMLIFrameElement | null>(null)

  function ensureDownloadFrame(): HTMLIFrameElement {
    if (downloadFrame.value) return downloadFrame.value
    const frame = document.createElement('iframe')
    frame.style.display = 'none'
    document.body.appendChild(frame)
    downloadFrame.value = frame
    return frame
  }

  function triggerDownload(url: string): void {
    const frame = ensureDownloadFrame()
    frame.onload = () => {
      try {
        const text = frame.contentDocument?.body?.innerText?.trim()
        if (!text) return
        const payload = JSON.parse(text) as { detail?: unknown }
        const detail = typeof payload.detail === 'string' ? payload.detail : null
        if (detail) options.onError(detail)
      } catch {}
    }
    frame.src = url
  }

  onBeforeUnmount(() => {
    downloadFrame.value?.remove()
    downloadFrame.value = null
  })

  return { triggerDownload }
}
