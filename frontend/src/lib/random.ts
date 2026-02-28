const CODE_ALPHABET = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'

export function randomCode(length: number): string {
  const out: string[] = []
  const max = CODE_ALPHABET.length
  for (let i = 0; i < length; i += 1) {
    const index = Math.floor(Math.random() * max)
    out.push(CODE_ALPHABET[index] as string)
  }
  return out.join('')
}
