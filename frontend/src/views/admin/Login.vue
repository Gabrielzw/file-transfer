<template>
  <div class="ft-page">
    <div class="login-wrap ft-card">
      <div class="login-head">
        <div class="ft-brand">
          <div class="ft-brand__title">文件中转站</div>
          <div class="ft-brand__sub">管理员登录</div>
        </div>
        <ThemeModeSwitch />
      </div>

      <el-form :model="form" @submit.prevent="onSubmit">
        <el-form-item>
          <el-input v-model="form.username" autocomplete="username" placeholder="账号" />
        </el-form-item>
        <el-form-item>
          <el-input
            v-model="form.password"
            autocomplete="current-password"
            type="password"
            placeholder="密码"
            show-password
          />
        </el-form-item>

        <el-button type="primary" :loading="loading" class="login-btn" @click="onSubmit">
          登录
        </el-button>
      </el-form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'

import { login } from '../../api/auth'
import { authToken } from '../../lib/auth'
import { isAxiosError } from '../../api/http'
import ThemeModeSwitch from '../../components/ThemeModeSwitch.vue'

const router = useRouter()
const route = useRoute()

const loading = ref(false)
const form = reactive({ username: '', password: '' })

async function onSubmit(): Promise<void> {
  if (loading.value) return
  loading.value = true
  try {
    const result = await login(form.username, form.password)
    authToken.set(result.token)
    const redirect = (route.query.redirect as string | undefined) ?? '/admin/files'
    await router.replace(redirect)
  } catch (error) {
    if (isAxiosError(error) && error.response?.status === 401) {
      ElMessage.error('账号或密码错误')
      return
    }
    ElMessage.error('登录失败')
    console.error(error)
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-wrap {
  width: min(420px, 100%);
  margin: 12vh auto 0;
  padding: 22px;
  border-radius: 18px;
  display: grid;
  gap: 18px;
}

.login-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
}

.login-btn {
  width: 100%;
}

@media (max-width: 640px) {
  .login-wrap {
    margin-top: 6vh;
    padding: 18px;
  }

  .login-head {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>
