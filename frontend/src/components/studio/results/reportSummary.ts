import type { ValidationCheck, ValidationReport } from "@/api/types"
import type { Status } from "@/components/shared/StatusTag"

/** FAIL = fail; PASS with expected violations = expected; otherwise pass. */
export function checkStatus(check: ValidationCheck): Status {
  if (check.status === "FAIL") return "fail"
  return check.expected_violations > 0 ? "expected" : "pass"
}

const minScore = (checks: ValidationCheck[]) => (checks.length ? Math.min(...checks.map((c) => c.score)) : null)

export interface ReportStats {
  uniqueKeys: number | null
  validLinks: number | null
  rulesPassed: number
  rulesTotal: number
  similarity: number | null
}

export function summarizeReport(report: ValidationReport): ReportStats {
  const pk = report.checks.filter((c) => c.name.startsWith("PK"))
  const fk = report.checks.filter((c) => c.name.startsWith("FK"))
  const rules = report.checks.filter((c) => c.name.startsWith("Rule"))
  return {
    uniqueKeys: minScore(pk),
    validLinks: minScore(fk),
    rulesPassed: rules.filter((c) => c.status === "PASS").length,
    rulesTotal: rules.length,
    similarity: report.similarity?.overall ?? null,
  }
}
