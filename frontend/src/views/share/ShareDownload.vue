<template>
  <div class="ft-page">
    <div class="ft-topbar">
      <div class="ft-brand">
        <div class="ft-brand__title">文件中转站</div>
        <div class="ft-brand__sub">访客下载</div>
      </div>

      <div class="ft-actions">
        <ThemeModeSwitch />
      </div>
    </div>

    <div class="ft-card panel" v-loading="loading">
      <template v-if="state === 'invalid'">
        <div class="invalid">
          <div class="invalid__title">{{ invalidTitle }}</div>
          <div class="invalid__sub">{{ invalidSub }}</div>
        </div>
      </template>

      <template v-else>
        <div class="meta">
          <div class="meta__name">{{ info?.filename }}</div>
          <div class="meta__sub">{{ info ? formatBytes(info.size) : '' }}</div>
        </div>

        <div v-if="info?.need_password" class="code">
          <el-input v-model="password" placeholder="请输入提取码" maxlength="8" />
        </div>

        <div class="actions">
          <el-button type="primary" :loading="verifying" @click="onDownload">
            {{ info?.need_password ? '验证并下载' : '下载' }}
          </el-button>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'

import { buildDownloadUrl, getShareInfo, verifyShare } from '../../api/share'
import { isAxiosError } from '../../api/http'
import { formatBytes } from '../../lib/format'
import ThemeModeSwitch from '../../components/ThemeModeSwitch.vue'

type State = 'ready' | 'invalid'

const route = useRoute()
const shareCode = String(route.params.shareCode ?? '')

const loading = ref(true)
const verifying = ref(false)
const state = ref<State>('ready')
const invalidTitle = ref('链接已失效')
const invalidSub = ref('该链接已过期或不存在')

const info = ref<{ filename: string; size: number; need_password: boolean } | null>(null)
const password = ref('')

async function load(): Promise<void> {
  loading.value = true
  try {
    info.value = await getShareInfo(shareCode)
    state.value = 'ready'
  } catch (error) {
    if (isAxiosError(error)) {
      if (error.response?.status === 410) {
        state.value = 'invalid'
        invalidTitle.value = '链接已失效'
        invalidSub.value = '该链接已过期或达到下载上限'
        return
      }
      if (error.response?.status === 404) {
        state.value = 'invalid'
        invalidTitle.value = '链接不存在'
        invalidSub.value = '请检查链接是否正确'
        return
      }
    }
    ElMessage.error('加载失败')
    console.error(error)
  } finally {
    loading.value = false
  }
}

async function onDownload(): Promise<void> {
  if (verifying.value || state.value !== 'ready') return
  verifying.value = true
  try {
    const res = await verifyShare(shareCode, info.value?.need_password ? password.value : null)
    window.location.href = buildDownloadUrl(shareCode, res.download_token)
  } catch (error) {
    if (isAxiosError(error) && error.response?.status === 422) {
      ElMessage.error('提取码错误')
      return
    }
    if (isAxiosError(error) && error.response?.status === 410) {
      await load()
      return
    }
    ElMessage.error('下载失败')
    console.error(error)
  } finally {
    verifying.value = false
  }
}

void load()
</script>

<style scoped>
.panel {
  border-radius: 18px;
  padding: 18px;
}

.meta__name {
  font-weight: 800;
  font-size: 18px;
}

.meta__sub {
  margin-top: 6px;
  color: var(--ft-text-dim);
  font-size: 12px;
}

.code {
  margin-top: 14px;
  max-width: 320px;
}

.actions {
  margin-top: 16px;
}

.invalid {
  display: grid;
  gap: 8px;
  padding: 6px 2px;
}

.invalid__title {
  font-weight: 800;
  font-size: 18px;
}

.invalid__sub {
  color: var(--ft-text-dim);
  font-size: 12px;
}

@media (max-width: 640px) {
  .code {
    max-width: none;
  }

  .actions :deep(.el-button) {
    width: 100%;
  }
}
</style>
