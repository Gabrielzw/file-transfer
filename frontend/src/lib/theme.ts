import { readonly, ref } from 'vue'

export type ThemeMode = 'light' | 'dark' | 'system'

const THEME_MODE_STORAGE_KEY = 'ft_theme_mode'
const SYSTEM_DARK_MEDIA_QUERY = '(prefers-color-scheme: dark)'

const themeMode = ref<ThemeMode>('system')

let systemDarkMediaQuery: MediaQueryList | null = null
let systemDarkListener: (() => void) | null = null
let warnedMissingMatchMedia = false

function isThemeMode(value: unknown): value is ThemeMode {
  return value === 'light' || value === 'dark' || value === 'system'
}

function readStoredThemeMode(): ThemeMode {
  const raw = localStorage.getItem(THEME_MODE_STORAGE_KEY)
  if (raw === null) return 'system'
  if (isThemeMode(raw)) return raw
  console.error(`[theme] invalid stored theme mode: ${raw}`)
  localStorage.removeItem(THEME_MODE_STORAGE_KEY)
  return 'system'
}

function getSystemDarkMediaQuery(): MediaQueryList | null {
  if (systemDarkMediaQuery) return systemDarkMediaQuery
  if (!window.matchMedia) {
    if (!warnedMissingMatchMedia) {
      warnedMissingMatchMedia = true
      console.error('[theme] window.matchMedia is not available; "system" theme will behave as "light".')
    }
    return null
  }
  systemDarkMediaQuery = window.matchMedia(SYSTEM_DARK_MEDIA_QUERY)
  return systemDarkMediaQuery
}

function resolveEffectiveTheme(mode: ThemeMode): 'light' | 'dark' {
  if (mode === 'light' || mode === 'dark') return mode
  const mql = getSystemDarkMediaQuery()
  if (!mql) return 'light'
  return mql.matches ? 'dark' : 'light'
}

function applyEffectiveTheme(effective: 'light' | 'dark'): void {
  const root = document.documentElement
  root.classList.toggle('dark', effective === 'dark')
  root.dataset.theme = effective
}

function detachSystemListener(): void {
  if (!systemDarkMediaQuery || !systemDarkListener) return
  systemDarkMediaQuery.removeEventListener('change', systemDarkListener)
  systemDarkListener = null
}

function attachSystemListener(): void {
  const mql = getSystemDarkMediaQuery()
  if (!mql || systemDarkListener) return
  systemDarkListener = () => {
    if (themeMode.value !== 'system') return
    applyEffectiveTheme(resolveEffectiveTheme('system'))
  }
  mql.addEventListener('change', systemDarkListener)
}

function applyThemeMode(mode: ThemeMode): void {
  if (mode === 'system') attachSystemListener()
  else detachSystemListener()

  document.documentElement.dataset.themeMode = mode
  applyEffectiveTheme(resolveEffectiveTheme(mode))
}

export function initTheme(): void {
  const mode = readStoredThemeMode()
  themeMode.value = mode
  applyThemeMode(mode)
}

export function setThemeMode(nextMode: ThemeMode): void {
  if (!isThemeMode(nextMode)) {
    throw new Error(`[theme] invalid theme mode: ${String(nextMode)}`)
  }
  themeMode.value = nextMode
  localStorage.setItem(THEME_MODE_STORAGE_KEY, nextMode)
  applyThemeMode(nextMode)
}

export function useThemeMode() {
  return readonly(themeMode)
}
