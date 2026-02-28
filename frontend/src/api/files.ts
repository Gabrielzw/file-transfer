import type { AxiosProgressEvent } from 'axios'

import { getApiBase, http } from './http'

export type ShareSummary = {
  share_code: string
  expire_at: string | null
  max_downloads: number | null
  download_count: number
  need_password: boolean
  share_url: string
}

export type FileItem = {
  id: string
  filename: string
  size: number
  mime_type: string
  remark: string | null
  created_at: string
  active_share: ShareSummary | null
}

export type FileListResponse = {
  total: number
  list: FileItem[]
}

export type UploadResponse = {
  file_id: string
  filename: string
  size: number
}

export type FileDownloadTokenResponse = {
  download_token: string
  expires_in: number
}

export type CreateShareRequest = {
  password?: string | null
  expire_hours?: number | null
  max_downloads?: number | null
}

export type CreateShareResponse = {
  share_code: string
  share_url: string
  expire_at: string | null
}

export async function uploadFile(
  file: File,
  remark: string | null,
  onProgress?: (percent: number) => void
): Promise<UploadResponse> {
  const form = new FormData()
  form.append('file', file)
  if (remark) form.append('remark', remark)

  const { data } = await http.post<UploadResponse>('/files/upload', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress: (event: AxiosProgressEvent) => {
      const total = event.total ?? 0
      if (!total) return
      const percent = Math.round((event.loaded / total) * 100)
      onProgress?.(percent)
    }
  })
  return data
}

export async function listFiles(params: {
  page: number
  size: number
  keyword?: string
}): Promise<FileListResponse> {
  const { data } = await http.get<FileListResponse>('/files', { params })
  return data
}

export async function deleteFile(fileId: string): Promise<void> {
  await http.delete(`/files/${encodeURIComponent(fileId)}`)
}

export async function createFileDownloadToken(fileId: string): Promise<FileDownloadTokenResponse> {
  const { data } = await http.post<FileDownloadTokenResponse>(`/files/${encodeURIComponent(fileId)}/download-token`)
  return data
}

export function buildFileDownloadUrl(fileId: string, token: string): string {
  const base = getApiBase().replace(/\/$/, '')
  return `${base}/files/${encodeURIComponent(fileId)}/download?token=${encodeURIComponent(token)}`
}

export async function createShare(fileId: string, body: CreateShareRequest): Promise<CreateShareResponse> {
  const { data } = await http.post<CreateShareResponse>(`/files/${encodeURIComponent(fileId)}/share`, body)
  return data
}
