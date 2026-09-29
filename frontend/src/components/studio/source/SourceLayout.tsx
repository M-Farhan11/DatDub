import type { ReactNode } from "react"
import { PageHeader } from "@/components/shared/PageHeader"
import { SourceBackLink } from "./SourceBackLink"

interface SourceLayoutProps {
  title: string
  subtitle: string
  children: ReactNode
}

/** Shared frame for the four source sub-screens. */
export function SourceLayout({ title, subtitle, children }: SourceLayoutProps) {
  return (
    <div className="mx-auto w-full max-w-[880px] px-gutter-lg pt-10 pb-24 md:pt-12">
      <PageHeader title={title} subtitle={subtitle} back={<SourceBackLink />} />
      <div className="mt-8">{children}</div>
    </div>
  )
}
