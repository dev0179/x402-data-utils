"use client"

interface HeaderProps {
  walletAddress?: string
}

export function Header({ walletAddress }: HeaderProps) {
  return (
    <div className="sticky top-0 z-50 bg-background/95 backdrop-blur border-b border-border/50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex flex-col items-center gap-2 text-center">
        <div className="flex items-center gap-3">
          <div className="flex items-center justify-center w-11 h-11 rounded-xl bg-primary/15">
            <span className="text-2xl font-bold text-primary">x</span>
          </div>
          <div className="flex flex-col gap-1">
            <h1 className="text-3xl font-semibold tracking-tight text-foreground">x402 Data Utilities</h1>
            <p className="text-sm text-muted-foreground">Mock wallet-signed demo - no blockchain, no real addresses</p>
          </div>
        </div>
        <div className="flex items-center gap-2 flex-wrap justify-center text-[11px]">
          <span className="px-2 py-0.5 rounded-full bg-primary/10 text-primary font-semibold">Mock Local Wallet</span>
          <span className="px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-300 font-semibold">No Real Funds</span>
          <span className="px-2 py-0.5 rounded-full bg-slate-500/10 text-slate-200 font-semibold">No Blockchain Calls</span>
          {walletAddress && (
            <span className="px-2 py-0.5 rounded-full bg-card/80 border border-border/50 text-muted-foreground font-mono">
              Demo wallet: {walletAddress.slice(0, 6)}...{walletAddress.slice(-4)}
            </span>
          )}
        </div>
      </div>
    </div>
  )
}
