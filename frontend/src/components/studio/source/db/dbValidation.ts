export const SAMPLE_DEFAULT = 200
export const SAMPLE_MAX = 1000

export function sampleLimitError(value: string): string | null {
  const n = Number(value)
  if (value === "" || !Number.isInteger(n) || n < 1 || n > SAMPLE_MAX) {
    return `Enter a whole number from 1 to ${SAMPLE_MAX.toLocaleString("en-US")}.`
  }
  return null
}
