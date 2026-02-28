import axios, { AxiosError } from 'axios'

import { authToken } from '../lib/auth'

const API_BASE = import.meta.env.VITE_API_BASE ?? '/api'

export const http = axios.create({
  baseURL: API_BASE,
  timeout: 30_000
})

http.interceptors.request.use((config) => {
  const token = authToken.get()
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

export function isAxiosError(error: unknown): error is AxiosError {
  return axios.isAxiosError(error)
}

export function getApiBase(): string {
  return API_BASE
}

