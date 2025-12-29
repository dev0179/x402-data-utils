import { Loader2 } from "lucide-react"
import { cn } from "@/lib/utils"

interface StatusBadgeProps {
  statusCode: number | null
  loading: boolean
}

export function StatusBadge({ statusCode, loading }: StatusBadgeProps) {
  if (loading) {
    return (
      <div className="flex items-center gap-2 px-4 py-2 rounded-lg border border-border bg-card/50 backdrop-blur-sm">
        <Loader2 className="w-4 h-4 animate-spin text-primary" />
        <span className="text-sm font-semibold">Processing...</span>
      </div>
    )
  }

  if (statusCode === null) {
    return (
      <div className="flex items-center gap-2 px-4 py-2 rounded-lg border border-border bg-card/50 backdrop-blur-sm">
        <div className="w-2 h-2 rounded-full bg-muted-foreground/50" />
        <span className="text-sm font-semibold text-muted-foreground">Ready</span>
      </div>
    )
  }

  const isSuccess = statusCode === 200
  const isPaymentRequired = statusCode === 402
  const isError = statusCode === 0 || (statusCode >= 400 && statusCode !== 402)

  return (
    <div
      className={cn(
        "flex items-center gap-2 px-4 py-2 rounded-lg border backdrop-blur-sm font-semibold text-sm transition-all",
        isSuccess && "border-accent/50 bg-accent/10 text-accent",
        isPaymentRequired && "border-destructive/50 bg-destructive/10 text-destructive",
        isError && "border-destructive/50 bg-destructive/10 text-destructive",
      )}
    >
      <div
        className={cn(
          "w-2 h-2 rounded-full",
          isSuccess && "bg-accent animate-pulse",
          isPaymentRequired && "bg-destructive",
          isError && "bg-destructive",
        )}
      />
      <span>Status {statusCode}</span>
    </div>
  )
}
