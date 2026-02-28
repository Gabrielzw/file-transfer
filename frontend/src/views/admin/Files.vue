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
          multiple
          :show-file-list="true"
          :http-request="customUpload"
          :disabled="uploading"
        >
          <div class="upload-hint">
            <div class="upload-hint__title">拖拽文件到此处，或点击选择</div>
            <div class="upload-hint__sub">支持同时选择多个文件</div>
          </div>
        </el-upload>
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
import { computed, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { useRouter } from 'vue-router'

import type { FileItem } from '../../api/files'
import { buildFileDownloadUrl, createFileDownloadToken, deleteFile, listFiles, uploadFile } from '../../api/files'
import { isAxiosError } from '../../api/http'
import { authToken } from '../../lib/auth'
import { formatBytes, formatDateTime, formatExpire } from '../../lib/format'
import { useIframeDownload } from '../../lib/useIframeDownload'
import ThemeModeSwitch from '../../components/ThemeModeSwitch.vue'
import ShareDialog from './components/ShareDialog.vue'

type UploadProgressEvent = { percent: number }
type UploadRequest = {
  file: File
  onProgress?: (event: UploadProgressEvent) => void
  onSuccess?: (response: unknown) => void
  onError?: (error: unknown) => void
}

const router = useRouter()

const loading = ref(false)
const items = ref<FileItem[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const keyword = ref('')

const activeUploads = ref(0)
const uploading = computed(() => activeUploads.value > 0)

const shareDialogOpen = ref(false)
const shareFileId = ref('')

const { triggerDownload } = useIframeDownload({ onError: (message) => ElMessage.error(message) })
let refreshQueued = false

async function refresh(): Promise<void> {
  if (loading.value) {
    refreshQueued = true
    return
  }
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

  if (!refreshQueued) return
  refreshQueued = false
  await refresh()
}

async function customUpload(req: any): Promise<void> {
  const { file, onProgress, onSuccess, onError } = req as UploadRequest
  activeUploads.value += 1
  try {
    const result = await uploadFile(file, null, (p) => onProgress?.({ percent: p }))
    onSuccess?.(result)
    ElMessage.success(`${file.name} 上传成功`)
    void refresh()
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
    activeUploads.value -= 1
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

<style scoped src="./Files.css"></style>
