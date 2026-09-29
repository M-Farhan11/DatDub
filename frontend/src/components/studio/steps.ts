export const STEPS = ["Source", "Schema", "Configure", "Results", "Export"] as const
export type Step = (typeof STEPS)[number]
