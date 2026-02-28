<template>
  <el-dialog :model-value="open" title="生成分享链接" width="min(520px, 92vw)" @update:model-value="onDialogUpdate">
    <el-form label-width="96px">
      <el-form-item label="有效期">
        <el-select v-model="form.expirePreset">
          <el-option label="1天" value="1d" />
          <el-option label="7天" value="7d" />
          <el-option label="30天" value="30d" />
          <el-option label="自定义" value="custom" />
          <el-option label="永久" value="forever" />
        </el-select>
      </el-form-item>

      <el-form-item v-if="form.expirePreset === 'custom'" label="自定义">
        <div class="custom-expire">
          <el-input-number v-model="form.customDays" :min="1" :controls="true" />
          <div class="dim">天</div>
        </div>
      </el-form-item>

      <el-form-item label="提取码">
        <div class="code-row">
          <el-input v-model="form.password" placeholder="可选：4~8位字母数字" maxlength="8" />
          <el-button @click="genPassword">随机</el-button>
          <el-button @click="clearPassword">清空</el-button>
        </div>
      </el-form-item>

      <el-form-item label="下载上限">
        <el-input-number v-model="form.maxDownloads" :min="1" :controls="true" placeholder="可选" />
        <div class="dim">留空表示不限次数</div>
      </el-form-item>
    </el-form>

    <template #footer>
      <el-button :disabled="submitting" @click="close">取消</el-button>
      <el-button type="primary" :loading="submitting" @click="submit">生成</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'

import { createShare } from '../../../api/files'
import { isAxiosError } from '../../../api/http'
import { randomCode } from '../../../lib/random'

type Props = {
  open: boolean
  fileId: string
}

const props = defineProps<Props>()
const emit = defineEmits<{
  (e: 'update:open', value: boolean): void
  (e: 'created'): void
}>()

const submitting = ref(false)
const form = reactive({
  expirePreset: '7d',
  customDays: 7,
  password: '',
  maxDownloads: null as number | null
})

const expireHours = computed<number | null>(() => {
  if (form.expirePreset === 'forever') return null
  if (form.expirePreset === 'custom') return 24 * form.customDays
  if (form.expirePreset === '1d') return 24
  if (form.expirePreset === '7d') return 24 * 7
  return 24 * 30
})

function reset(): void {
  form.expirePreset = '7d'
  form.customDays = 7
  form.password = ''
  form.maxDownloads = null
}

watch(
  () => props.open,
  (open) => {
    if (open) reset()
  }
)

function close(): void {
  emit('update:open', false)
}

function onDialogUpdate(next: boolean): void {
  emit('update:open', next)
}

function genPassword(): void {
  form.password = randomCode(6)
}

function clearPassword(): void {
  form.password = ''
}

async function submit(): Promise<void> {
  if (!props.fileId) {
    ElMessage.error('未选择文件')
    return
  }
  if (submitting.value) return

  submitting.value = true
  try {
    const result = await createShare(props.fileId, {
      password: form.password || null,
      expire_hours: expireHours.value,
      max_downloads: form.maxDownloads
    })

    const code = form.password ? `提取码：${form.password}` : '无提取码'
    ElMessage.success(`已生成：${code}`)
    emit('created')
    close()

    try {
      await navigator.clipboard.writeText(
        form.password ? `链接：${result.share_url}\n提取码：${form.password}` : result.share_url
      )
      ElMessage.success('已复制到剪贴板')
    } catch (error) {
      ElMessage.warning('生成成功，但复制失败，请手动复制链接/提取码')
      console.error(error)
    }
  } catch (error) {
    if (isAxiosError(error)) {
      const detail = (error.response?.data as { detail?: string } | undefined)?.detail
      if (detail) ElMessage.error(detail)
      else ElMessage.error('生成失败')
      console.error(error)
      return
    }
    ElMessage.error('生成失败')
    console.error(error)
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.code-row {
  display: grid;
  grid-template-columns: 1fr auto auto;
  gap: 8px;
  width: 100%;
}

.dim {
  font-size: 12px;
  color: var(--ft-text-dim);
  margin-top: 6px;
}

.custom-expire {
  display: flex;
  align-items: center;
  gap: 10px;
}

@media (max-width: 480px) {
  .code-row {
    grid-template-columns: 1fr;
  }
}
</style>
