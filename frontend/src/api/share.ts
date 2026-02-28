import { getApiBase, http } from './http'

export type ShareInfoResponse = {
  filename: string
  size: number
  need_password: boolean
}

export type VerifyShareResponse = {
  download_token: string
  expires_in: number
}

export async function getShareInfo(shareCode: string): Promise<ShareInfoResponse> {
  const { data } = await http.get<ShareInfoResponse>(`/share/${encodeURIComponent(shareCode)}`)
  return data
}

export async function verifyShare(shareCode: string, password: string | null): Promise<VerifyShareResponse> {
  const { data } = await http.post<VerifyShareResponse>(`/share/${encodeURIComponent(shareCode)}/verify`, {
    password
  })
  return data
}

export function buildDownloadUrl(shareCode: string, token: string): string {
  const base = getApiBase().replace(/\/$/, '')
  return `${base}/share/${encodeURIComponent(shareCode)}/download?token=${encodeURIComponent(token)}`
}

