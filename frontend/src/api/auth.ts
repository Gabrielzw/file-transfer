import { http } from './http'

export type LoginResponse = {
  token: string
  expires_in: number
}

export async function login(username: string, password: string): Promise<LoginResponse> {
  const { data } = await http.post<LoginResponse>('/auth/login', { username, password })
  return data
}

