<template>
  <div class="ft-page">
    <div class="ft-topbar">
      <div class="ft-brand">
        <div class="ft-brand__title">文件中转站</div>
        <div class="ft-brand__sub">上传、生成链接、管理文件</div>
      </div>

      <div class="ft-actions">
        <ThemeModeSwitch />
        <el-button size="small" @click="onLogout">退出登录</el-button>
      </div>
    </div>

    <div class="grid">
      <div class="ft-card panel panel--upload">
        <div class="panel__title">上传</div>
        <el-upload
          drag
          :show-file-list="false"
          :http-request="customUpload"
          :disabled="uploading"
        >
          <div class="upload-hint">
            <div class="upload-hint__title">拖拽文件到此处，或点击选择</div>
            <div class="upload-hint__sub">单次仅支持一个文件</div>
          </div>
        </el-upload>
        <el-progress v-if="uploading" :percentage="uploadPercent" :stroke-width="10" />
      </div>

      <div class="ft-card panel panel--list">
        <div class="panel__header">
          <div class="panel__title">文件列表</div>
          <div class="panel__tools">
            <el-input
              v-model="keyword"
              placeholder="搜索文件名/备注"
              clearable
              @keyup.enter="refresh"
            />
            <el-button type="primary" @click="refresh">刷新</el-button>
          </div>
        </div>

        <div class="file-cards" v-loading="loading">
          <el-empty v-if="!loading && items.length === 0" description="暂无文件" />

          <div v-for="row in items" :key="row.id" class="file-card">
            <div class="file-card__head">
              <div class="file-card__name">{{ row.filename }}</div>
              <el-tag v-if="row.active_share" type="success" size="small">已分享</el-tag>
              <el-tag v-else type="info" size="small">未分享</el-tag>
            </div>

            <div class="file-card__meta">
              {{ formatBytes(row.size) }} · {{ formatDateTime(row.created_at) }}
            </div>
            <div class="file-card__meta">
              有效期：{{ row.active_share ? formatExpire(row.active_share.expire_at) : '—' }}
            </div>

            <div class="file-card__ops">
              <el-button size="small" @click="onDownload(row)">下载</el-button>
              <el-button size="small" type="primary" @click="openShare(row)">
                {{ row.active_share ? '重新生成' : '生成链接' }}
              </el-button>
              <el-button size="small" :disabled="!row.active_share" @click="copyShare(row)">
                复制
              </el-button>
              <el-popconfirm title="确认删除该文件？" @confirm="onDelete(row.id)">
                <template #reference>
                  <el-button size="small" type="danger">删除</el-button>
                </template>
              </el-popconfirm>
            </div>
          </div>
        </div>

        <el-table :data="items" v-loading="loading" class="table">
          <el-table-column label="文件名" min-width="220">
            <template #default="{ row }">
              <div class="name">
                <div class="name__main">{{ row.filename }}</div>
                <div class="name__sub">{{ formatBytes(row.size) }} · {{ formatDateTime(row.created_at) }}</div>
              </div>
            </template>
          </el-table-column>

          <el-table-column label="有效期" width="180">
            <template #default="{ row }">
              {{ row.active_share ? formatExpire(row.active_share.expire_at) : '—' }}
            </template>
          </el-table-column>

          <el-table-column label="分享状态" width="120">
            <template #default="{ row }">
              <el-tag v-if="row.active_share" type="success">已分享</el-tag>
              <el-tag v-else type="info">未分享</el-tag>
            </template>
          </el-table-column>

          <el-table-column label="操作" width="320">
            <template #default="{ row }">
              <div class="ops">
                <el-button size="small" @click="onDownload(row)">下载</el-button>
                <el-button size="small" type="primary" @click="openShare(row)">
                  {{ row.active_share ? '重新生成' : '生成链接' }}
                </el-button>
                <el-button
                  size="small"
                  :disabled="!row.active_share"
                  @click="copyShare(row)"
                >
                  复制
                </el-button>
                <el-popconfirm title="确认删除该文件？" @confirm="onDelete(row.id)">
                  <template #reference>
                    <el-button size="small" type="danger">删除</el-button>
                  </template>
                </el-popconfirm>
              </div>
            </template>
          </el-table-column>
        </el-table>

        <div class="pager">
          <el-pagination
            background
            layout="prev, pager, next"
            :page-size="pageSize"
            :total="total"
            :current-page="page"
            @current-change="onPageChange"
          />
        </div>
      </div>
    </div>

    <ShareDialog v-model:open="shareDialogOpen" :file-id="shareFileId" @created="refresh" />
  </div>
</template>

<script setup lang="ts">
import { onBeforeUnmount, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { useRouter } from 'vue-router'

import type { FileItem } from '../../api/files'
import { buildFileDownloadUrl, createFileDownloadToken, deleteFile, listFiles, uploadFile } from '../../api/files'
import { isAxiosError } from '../../api/http'
import { authToken } from '../../lib/auth'
import { formatBytes, formatDateTime, formatExpire } from '../../lib/format'
import ThemeModeSwitch from '../../components/ThemeModeSwitch.vue'
import ShareDialog from './components/ShareDialog.vue'

type UploadRequest = { file: File }

const router = useRouter()

const loading = ref(false)
const items = ref<FileItem[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const keyword = ref('')

const uploading = ref(false)
const uploadPercent = ref(0)

const shareDialogOpen = ref(false)
const shareFileId = ref('')

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
      if (detail) ElMessage.error(detail)
    } catch {}
  }
  frame.src = url
}

onBeforeUnmount(() => {
  downloadFrame.value?.remove()
  downloadFrame.value = null
})

async function refresh(): Promise<void> {
  if (loading.value) return
  loading.value = true
  try {
    const res = await listFiles({
      page: page.value,
      size: pageSize.value,
      keyword: keyword.value || undefined
    })
    items.value = res.list
    total.value = res.total
  } catch (error) {
    if (isAxiosError(error) && error.response?.status === 401) {
      authToken.clear()
      await router.replace('/admin/login')
      return
    }
    ElMessage.error('加载失败')
    console.error(error)
  } finally {
    loading.value = false
  }
}

async function customUpload(req: any): Promise<void> {
  const file = (req as UploadRequest).file
  if (uploading.value) return
  uploading.value = true
  uploadPercent.value = 0
  try {
    await uploadFile(file, null, (p) => (uploadPercent.value = p))
    ElMessage.success('上传成功')
    await refresh()
  } catch (error) {
    if (isAxiosError(error) && error.response?.status === 413) {
      const detail = (error.response?.data as { detail?: string } | undefined)?.detail
      ElMessage.error(detail ?? '文件过大')
      return
    }
    ElMessage.error('上传失败')
    console.error(error)
  } finally {
    uploading.value = false
  }
}

async function onDelete(fileId: string): Promise<void> {
  try {
    await deleteFile(fileId)
    ElMessage.success('已删除')
    await refresh()
  } catch (error) {
    ElMessage.error('删除失败')
    console.error(error)
  }
}

function openShare(row: FileItem): void {
  shareFileId.value = row.id
  shareDialogOpen.value = true
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

async function onDownload(row: FileItem): Promise<void> {
  try {
    const res = await createFileDownloadToken(row.id)
    const url = buildFileDownloadUrl(row.id, res.download_token)
    triggerDownload(url)
  } catch (error) {
    if (isAxiosError(error) && error.response?.status === 401) {
      authToken.clear()
      await router.replace('/admin/login')
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

async function onLogout(): Promise<void> {
  authToken.clear()
  await router.replace('/admin/login')
}

async function onPageChange(next: number): Promise<void> {
  page.value = next
  await refresh()
}

void refresh()
</script>

<style scoped>
.grid {
  display: grid;
  grid-template-columns: 360px 1fr;
  gap: 14px;
  align-items: start;
}

.panel {
  border-radius: 18px;
  padding: 16px;
}

.panel__header {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: center;
  margin-bottom: 10px;
}

.panel__title {
  font-weight: 700;
  letter-spacing: 0.2px;
}

.panel__tools {
  display: flex;
  gap: 10px;
  align-items: center;
}

.file-cards {
  display: none;
  position: relative;
}

.file-card {
  background: var(--ft-surface-2);
  border: 1px solid var(--ft-border);
  border-radius: 16px;
  padding: 14px;
}

.file-card__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
}

.file-card__name {
  font-weight: 800;
  line-height: 1.25;
  overflow-wrap: anywhere;
}

.file-card__meta {
  margin-top: 6px;
  font-size: 12px;
  color: var(--ft-text-dim);
}

.file-card__ops {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 12px;
}

.upload-hint {
  display: grid;
  gap: 4px;
}

.upload-hint__title {
  font-weight: 700;
}

.upload-hint__sub {
  font-size: 12px;
  color: var(--ft-text-dim);
}

.name__main {
  font-weight: 700;
}

.name__sub {
  font-size: 12px;
  color: var(--ft-text-dim);
  margin-top: 4px;
}

.ops {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.pager {
  display: flex;
  justify-content: flex-end;
  padding-top: 12px;
}

@media (max-width: 980px) {
  .grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 900px), (hover: none) and (pointer: coarse) {
  .table {
    display: none;
  }

  .file-cards {
    display: grid;
    gap: 12px;
  }

  .panel__header {
    flex-direction: column;
    align-items: stretch;
  }

  .panel__tools {
    width: 100%;
    flex-direction: column;
    align-items: stretch;
  }

  .panel__tools :deep(.el-button) {
    width: 100%;
  }

  .pager {
    justify-content: center;
  }

  .pager :deep(.el-pagination) {
    flex-wrap: wrap;
    justify-content: center;
  }
}
</style>
