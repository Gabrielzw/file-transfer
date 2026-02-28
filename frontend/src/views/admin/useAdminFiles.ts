import { computed, ref } from 'vue'
import type { Ref } from 'vue'
import { ElMessage } from 'element-plus'
import { useRouter } from 'vue-router'
import type { Router } from 'vue-router'

import type { FileItem } from '../../api/files'
import { buildFileDownloadUrl, createFileDownloadToken, deleteFile, listFiles, uploadFile } from '../../api/files'
import { isAxiosError } from '../../api/http'
import { authToken } from '../../lib/auth'
import { useIframeDownload } from '../../lib/useIframeDownload'

type UploadProgressEvent = { percent: number }
type UploadRequest = {
  file: File
  onProgress?: (event: UploadProgressEvent) => void
  onSuccess?: (response: unknown) => void
  onError?: (error: unknown) => void
}

type RefreshContext = {
  router: Router
  loading: Ref<boolean>
  items: Ref<FileItem[]>
  total: Ref<number>
  page: Ref<number>
  pageSize: Ref<number>
  keyword: Ref<string>
  selectedIds: Ref<string[]>
  refreshQueued: Ref<boolean>
}

type UploadContext = {
  activeUploads: Ref<number>
  refresh: () => Promise<void>
}

type DeleteOneContext = {
  router: Router
  refresh: () => Promise<void>
}

type DeleteSelectedContext = {
  router: Router
  refresh: () => Promise<void>
  selectedIds: Ref<string[]>
  deleting: Ref<boolean>
}

type DownloadContext = {
  router: Router
  triggerDownload: (url: string) => void
}

const DEFAULT_PAGE_SIZE = 20

function isUnauthorized(error: unknown): boolean {
  return isAxiosError(error) && error.response?.status === 401
}

async function redirectToLogin(router: Router): Promise<void> {
  authToken.clear()
  await router.replace('/admin/login')
}

function keepVisibleSelection(ids: readonly string[], list: readonly FileItem[]): string[] {
  if (ids.length === 0) return []
  const visible = new Set(list.map((item) => item.id))
  return ids.filter((id) => visible.has(id))
}

async function refreshFiles(ctx: RefreshContext): Promise<void> {
  if (ctx.loading.value) {
    ctx.refreshQueued.value = true
    return
  }

  ctx.loading.value = true
  try {
    const res = await listFiles({
      page: ctx.page.value,
      size: ctx.pageSize.value,
      keyword: ctx.keyword.value || undefined
    })
    ctx.items.value = res.list
    ctx.total.value = res.total
    ctx.selectedIds.value = keepVisibleSelection(ctx.selectedIds.value, res.list)
  } catch (error) {
    if (isUnauthorized(error)) {
      await redirectToLogin(ctx.router)
      return
    }
    ElMessage.error('加载失败')
    console.error(error)
  } finally {
    ctx.loading.value = false
  }

  if (!ctx.refreshQueued.value) return
  ctx.refreshQueued.value = false
  await refreshFiles(ctx)
}

async function customUpload(ctx: UploadContext, req: unknown): Promise<void> {
  const { file, onProgress, onSuccess, onError } = req as UploadRequest
  ctx.activeUploads.value += 1
  try {
    const result = await uploadFile(file, null, (p) => onProgress?.({ percent: p }))
    onSuccess?.(result)
    ElMessage.success(`${file.name} 上传成功`)
    void ctx.refresh()
  } catch (error) {
    onError?.(error)
    if (isAxiosError(error) && error.response?.status === 413) {
      const detail = (error.response?.data as { detail?: string } | undefined)?.detail
      ElMessage.error(detail ?? '文件过大')
      return
    }
    ElMessage.error('上传失败')
    console.error(error)
  } finally {
    ctx.activeUploads.value -= 1
  }
}

async function deleteOne(ctx: DeleteOneContext, fileId: string): Promise<void> {
  try {
    await deleteFile(fileId)
    ElMessage.success('已删除')
    await ctx.refresh()
  } catch (error) {
    if (isUnauthorized(error)) {
      await redirectToLogin(ctx.router)
      return
    }
    ElMessage.error('删除失败')
    console.error(error)
  }
}

async function deleteMany(ids: readonly string[]): Promise<{
  succeeded: string[]
  failed: Array<{ id: string; error: unknown }>
}> {
  const results = await Promise.allSettled(ids.map((id) => deleteFile(id)))
  const succeeded: string[] = []
  const failed: Array<{ id: string; error: unknown }> = []
  results.forEach((result, index) => {
    const id = ids[index]
    if (result.status === 'fulfilled') succeeded.push(id)
    else failed.push({ id, error: result.reason })
  })
  return { succeeded, failed }
}

async function deleteSelected(ctx: DeleteSelectedContext): Promise<void> {
  const ids = ctx.selectedIds.value
  if (ids.length === 0 || ctx.deleting.value) return

  ctx.deleting.value = true
  try {
    const { succeeded, failed } = await deleteMany(ids)
    if (failed.some((item) => isUnauthorized(item.error))) {
      await redirectToLogin(ctx.router)
      return
    }

    if (failed.length === 0) {
      ElMessage.success(`已删除 ${succeeded.length} 个文件`)
      ctx.selectedIds.value = []
    } else {
      ElMessage.error(`删除失败：${failed.length}/${ids.length}`)
      failed.forEach((item) => console.error(item.error))
      ctx.selectedIds.value = failed.map((item) => item.id)
    }

    await ctx.refresh()
  } finally {
    ctx.deleting.value = false
  }
}

function onTableSelectionChange(selectedIds: Ref<string[]>, rows: FileItem[]): void {
  selectedIds.value = rows.map((row) => row.id)
}

async function copyShare(row: FileItem): Promise<void> {
  if (!row.active_share) return
  try {
    await navigator.clipboard.writeText(row.active_share.share_url)
    ElMessage.success('已复制到剪贴板')
  } catch (error) {
    ElMessage.error('复制失败')
    console.error(error)
  }
}

async function downloadOne(ctx: DownloadContext, row: FileItem): Promise<void> {
  try {
    const res = await createFileDownloadToken(row.id)
    const url = buildFileDownloadUrl(row.id, res.download_token)
    ctx.triggerDownload(url)
  } catch (error) {
    if (isUnauthorized(error)) {
      await redirectToLogin(ctx.router)
      return
    }
    if (isAxiosError(error)) {
      const detail = (error.response?.data as { detail?: string } | undefined)?.detail
      ElMessage.error(detail ?? '下载失败')
      console.error(error)
      return
    }
    ElMessage.error('下载失败')
    console.error(error)
  }
}

export function useAdminFiles() {
  const router = useRouter()

  const loading = ref(false)
  const items = ref<FileItem[]>([])
  const total = ref(0)
  const page = ref(1)
  const pageSize = ref(DEFAULT_PAGE_SIZE)
  const keyword = ref('')
  const selectedIds = ref<string[]>([])
  const refreshQueued = ref(false)

  const refresh = () => refreshFiles({ router, loading, items, total, page, pageSize, keyword, selectedIds, refreshQueued })

  const activeUploads = ref(0)
  const uploading = computed(() => activeUploads.value > 0)
  const customUploadHandler = (req: unknown): Promise<void> => customUpload({ activeUploads, refresh }, req)

  const deleting = ref(false)
  const onDelete = (fileId: string): Promise<void> => deleteOne({ router, refresh }, fileId)
  const onDeleteSelected = (): Promise<void> => deleteSelected({ router, refresh, selectedIds, deleting })
  const onSelectionChange = (rows: FileItem[]): void => onTableSelectionChange(selectedIds, rows)

  const { triggerDownload } = useIframeDownload({ onError: (message) => ElMessage.error(message) })
  const onDownload = (row: FileItem): Promise<void> => downloadOne({ router, triggerDownload }, row)

  const onLogout = (): Promise<void> => redirectToLogin(router)
  const onPageChange = async (next: number): Promise<void> => { page.value = next; await refresh() }

  return { loading, deleting, uploading, items, total, page, pageSize, keyword, selectedIds, refresh, customUpload: customUploadHandler, onDelete, onDeleteSelected, onTableSelectionChange: onSelectionChange, copyShare, onDownload, onLogout, onPageChange }
}
