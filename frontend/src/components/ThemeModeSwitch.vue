<template>
  <el-segmented
    class="ft-theme-toggle"
    size="small"
    :model-value="themeMode"
    :options="options"
    aria-label="主题模式"
    @update:model-value="onThemeModeUpdate"
  />
</template>

<script setup lang="ts">
import { setThemeMode, useThemeMode, type ThemeMode } from '../lib/theme'

const themeMode = useThemeMode()
const options: Array<{ label: string; value: ThemeMode }> = [
  { label: '浅色', value: 'light' },
  { label: '深色', value: 'dark' },
  { label: '跟随系统', value: 'system' }
]

function onThemeModeUpdate(value: string | number | boolean): void {
  if (value === 'light' || value === 'dark' || value === 'system') {
    setThemeMode(value)
    return
  }
  throw new Error(`[theme] invalid theme mode from segmented: ${String(value)}`)
}
</script>

