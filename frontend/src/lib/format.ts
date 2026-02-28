const BYTES_PER_KIB = 1024
const BYTES_PER_MIB = BYTES_PER_KIB * BYTES_PER_KIB
const BYTES_PER_GIB = BYTES_PER_MIB * BYTES_PER_KIB

export function formatBytes(size: number): string {
  if (size < BYTES_PER_KIB) return `${size} B`
  if (size < BYTES_PER_MIB) return `${(size / BYTES_PER_KIB).toFixed(1)} KiB`
  if (size < BYTES_PER_GIB) return `${(size / BYTES_PER_MIB).toFixed(1)} MiB`
  return `${(size / BYTES_PER_GIB).toFixed(2)} GiB`
}

export function formatDateTime(iso: string): string {
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return iso
  return date.toLocaleString()
}

export function formatExpire(iso: string | null): string {
  if (!iso) return '永久'
  return formatDateTime(iso)
}

