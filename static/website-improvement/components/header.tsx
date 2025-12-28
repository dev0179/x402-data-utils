"use client"

import { Switch } from "@/components/ui/switch"

interface HeaderProps {
  isPaid: boolean
  setIsPaid: (isPaid: boolean) => void
  timeline: { label: string; detail: string }[]
}

export function Header({ isPaid, setIsPaid, timeline }: HeaderProps) {
  return (
    <div className="border-b border-border/50 backdrop-blur-sm sticky top-0 z-50 bg-background/80">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <div className="flex flex-col items-center gap-4 mb-6 text-center">
          <div className="flex items-center gap-3">
            <div className="flex items-center justify-center w-10 h-10 rounded-xl bg-gradient-to-br from-primary to-accent">
              <span className="text-xl font-bold text-primary-foreground">x</span>
            </div>
            <div>
              <h1 className="text-2xl font-bold tracking-tight text-balance">x402 Paywall Sandbox</h1>
              <p className="text-sm text-muted-foreground">Mock 402 → 200 switch for the data utilities</p>
            </div>
          </div>
        </div>

        <div className="flex flex-col sm:flex-row sm:items-center gap-4 justify-center">
          <div className="flex items-center gap-3 px-4 py-3 rounded-xl border border-border bg-card/50 backdrop-blur-sm">
            <Switch checked readOnly className="data-[state=checked]:bg-primary opacity-60" />
            <div className="flex-1">
              <label className="text-sm font-semibold cursor-pointer">Auto Mock Handshake</label>
              <p className="text-xs text-muted-foreground">Unpaid → 402 → auto retry with X-X402-Mock-Paid (always on)</p>
            </div>
          </div>
        </div>
      </div>
      <div className="fixed top-14 right-4 z-50 w-96 rounded-xl border border-border bg-card/90 backdrop-blur-md shadow-2xl p-4 space-y-3">
        <div className="text-sm font-semibold">Handshake Timeline</div>
        <div className="space-y-1 font-mono text-xs max-h-64 overflow-y-auto bg-black/30 p-3 rounded-lg">
          {timeline.length === 0 ? (
            <div className="text-muted-foreground">No events yet</div>
          ) : (
            timeline.map((evt, idx) => (
              <div key={idx} className="flex gap-2">
                <span className="text-muted-foreground">{`[${idx + 1}]`}</span>
                <span>{evt.label}</span>
                <span className="text-muted-foreground truncate">{evt.detail}</span>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  )
}
