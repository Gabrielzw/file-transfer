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
            <el-popconfirm
              :disabled="selectedIds.length === 0 || deleting"
              :title="`确认删除选中的 ${selectedIds.length} 个文件？`"
              @confirm="onDeleteSelected"
            >
              <template #reference>
                <el-button
                  type="danger"
                  :loading="deleting"
                  :disabled="selectedIds.length === 0"
                >
                  删除选中（{{ selectedIds.length }}）
                </el-button>
              </template>
            </el-popconfirm>
          </div>
        </div>

        <div class="file-cards-toolbar">
          <el-checkbox
            :model-value="allVisibleSelected"
            :indeterminate="visibleSelectionIndeterminate"
            :disabled="loading || deleting || items.length === 0"
            @change="toggleVisibleSelection"
          >
            全选
          </el-checkbox>
          <div class="file-cards-toolbar__count">已选 {{ selectedIds.length }} / {{ items.length }}</div>
        </div>

        <el-checkbox-group v-model="selectedIds" class="file-cards" v-loading="loading">
          <el-empty v-if="!loading && items.length === 0" description="暂无文件" />

          <div v-for="row in items" :key="row.id" class="file-card">
            <div class="file-card__head">
              <el-checkbox :label="row.id" :disabled="deleting" class="file-card__select">
                <span class="file-card__name">{{ row.filename }}</span>
              </el-checkbox>
              <el-tag v-if="row.active_share" type="success" size="small">已分享</el-tag>
              <el-tag v-else type="info" size="small">未分享</el-tag>
            </div>

            <div class="file-card__meta">
              <span class="file-card__meta-label">大小</span>
              <span class="file-card__meta-value">{{ formatBytes(row.size) }}</span>
              <span class="file-card__meta-label">上传时间</span>
              <span class="file-card__meta-value">{{ formatDateTime(row.created_at) }}</span>
              <span class="file-card__meta-label">有效期</span>
              <span class="file-card__meta-value">
                {{ row.active_share ? formatExpire(row.active_share.expire_at) : '—' }}
              </span>
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
        </el-checkbox-group>

        <el-table
          :data="items"
          v-loading="loading"
          class="table"
          row-key="id"
          @selection-change="onTableSelectionChange"
        >
          <el-table-column type="selection" width="48" />
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

import type { FileItem } from '../../api/files'
import { formatBytes, formatDateTime, formatExpire } from '../../lib/format'
import ThemeModeSwitch from '../../components/ThemeModeSwitch.vue'
import ShareDialog from './components/ShareDialog.vue'
import { useAdminFiles } from './useAdminFiles'

const shareDialogOpen = ref(false)
const shareFileId = ref('')

const {
  loading,
  deleting,
  uploading,
  items,
  total,
  page,
  pageSize,
  keyword,
  selectedIds,
  refresh,
  customUpload,
  onDelete,
  onDeleteSelected,
  onTableSelectionChange,
  copyShare,
  onDownload,
  onLogout,
  onPageChange
} = useAdminFiles()

const visibleIds = computed(() => items.value.map((item) => item.id))
const allVisibleSelected = computed(
  () => visibleIds.value.length > 0 && selectedIds.value.length === visibleIds.value.length
)
const visibleSelectionIndeterminate = computed(() => {
  const selectedCount = selectedIds.value.length
  const totalCount = visibleIds.value.length
  return selectedCount > 0 && selectedCount < totalCount
})

function toggleVisibleSelection(checked: boolean): void {
  selectedIds.value = checked ? [...visibleIds.value] : []
}

function openShare(row: FileItem): void {
  shareFileId.value = row.id
  shareDialogOpen.value = true
}

void refresh()
</script>

<style scoped src="./Files.css"></style>
