"use client"

import { useEffect, useState } from "react"
import { Header } from "@/components/header"
import { ApiEndpoint } from "@/components/api-endpoint"
import { ResultsPanel } from "@/components/results-panel"
import { StatusBadge } from "@/components/status-badge"
import { ethers, HDNodeWallet } from "ethers"

export default function Home() {
  const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000"
  const [statusCode, setStatusCode] = useState<number | null>(null)
  const [loading, setLoading] = useState(false)
  const [responseHeaders, setResponseHeaders] = useState<Record<string, string>>({})
  const [responseBody, setResponseBody] = useState<any>(null)
  const [errorCount, setErrorCount] = useState<number>(0)
  const [warningCount, setWarningCount] = useState<number>(0)
  const [errors, setErrors] = useState<any[]>([])
  const [lastValidationResult, setLastValidationResult] = useState<any>(null)
  const [lastCsv, setLastCsv] = useState<string | null>(null)
  const [timeline, setTimeline] = useState<{ label: string; detail: string; status?: number }[]>([])
  const [wallet, setWallet] = useState<HDNodeWallet | null>(null)
  const [requestCount, setRequestCount] = useState(0)
  const [totalSpent, setTotalSpent] = useState(0)

  useEffect(() => {
    // Create an ephemeral wallet on the client to avoid SSR/random hydration mismatch.
    const w = ethers.Wallet.createRandom() as HDNodeWallet
    setWallet(w)
  }, [])

  const handleRequest = async (path: string, options: RequestInit) => {
    setLoading(true)
    setStatusCode(null)
    setRequestCount((c) => c + 1)

    const headers = new Headers(options.headers)
    const events: { label: string; detail: string; status?: number }[] = []

    try {
      events.push({ label: `Sent ${options.method || "POST"}`, detail: path })

      // start unpaid attempt
      let res = await fetch(`${API_BASE}${path}`, {
        ...options,
        headers,
      })
      let contentType = res.headers.get("content-type") || ""
      let body = contentType.includes("application/json") ? await res.json() : await res.text()

      // If 402, show payment info and retry automatically
      if (res.status === 402) {
        const price =
          res.headers.get("x-x402-price") ||
          (body && body.price) ||
          (body && body.invoice && body.invoice.price)
        const payTo =
          res.headers.get("x-x402-payto") ||
          (body && body.pay_to) ||
          (body && body.invoice && body.invoice.pay_to)
        const mode = res.headers.get("x-x402-mode") || body?.mode || "wallet"
        const invoiceId = body?.invoice?.invoice_id
        events.push({
          label: "Received 402",
          detail: `price=${price || "-"}\npay_to=${payTo || "-"}\nmode=${mode}\ninvoice_id=${invoiceId || "-"}`,
          status: 402,
        })

        if (mode === "wallet" && body?.invoice) {
          if (!wallet) {
            throw new Error("Wallet not ready")
          }
          // Sign invoice with local ephemeral wallet
          const inv = body.invoice
          const msg = `x402-local-wallet|invoice_id=${inv.invoice_id}|path=${inv.path}|price=${inv.price}|pay_to=${inv.pay_to}|nonce=${inv.nonce}|expires_at=${inv.expires_at}`
          const signature = await wallet.signMessage(msg)
          const proof = {
            invoice: inv,
            payer: wallet.address,
            signature,
          }
          const proofB64 = btoa(JSON.stringify(proof))
          headers.set("X-X402-Proof", proofB64)
          events.push({ label: "Signing", detail: `payer=${wallet.address}` })
          events.push({ label: "Retrying", detail: "with X-X402-Proof" })
        }

        res = await fetch(`${API_BASE}${path}`, {
          ...options,
          headers,
        })
        contentType = res.headers.get("content-type") || ""
        body = contentType.includes("application/json") ? await res.json() : await res.text()
      }

      setStatusCode(res.status)

      // Extract response headers
      const headersObj: Record<string, string> = {}
      res.headers.forEach((value, key) => {
        headersObj[key] = value
      })
      setResponseHeaders(headersObj)
      setResponseBody(body)

      // Handle validation results
      if (body && typeof body === "object" && body.csv) {
        setLastCsv(body.csv)
      } else {
        setLastCsv(null)
      }
      if (path === "/validate/csv" && typeof body === "object") {
        setLastValidationResult(body)
        setErrorCount(body.errors?.length || 0)
        setWarningCount(body.warnings?.length || 0)
        setErrors(body.errors?.slice(0, 20) || [])
      } else {
        setLastValidationResult(null)
        setErrorCount(0)
        setWarningCount(0)
        setErrors([])
      }

      // Timeline entries based on response
      const settled = res.headers.get("x-x402-receipt") || res.headers.get("x-x402-payer")
      const receipt = res.headers.get("x-x402-receipt")
      const priceHeader =
        res.headers.get("x-x402-price") ||
        (body && body.price) ||
        (body && (body as any).invoice && (body as any).invoice.price)
      events.push({
        label: `Received ${res.status}`,
        detail: settled ? `settled=${settled}${receipt ? `\nreceipt=${receipt}` : ""}` : "",
        status: res.status,
      })
      if (res.status >= 200 && res.status < 300 && priceHeader) {
        const parsed = Number.parseFloat(String(priceHeader))
        if (!Number.isNaN(parsed)) {
          setTotalSpent((t) => t + parsed)
        }
      }
      setTimeline(events)
    } catch (err) {
      setStatusCode(0)
      setResponseBody({ error: "Network error", message: String(err) })
      setTimeline([{ label: "Error", detail: String(err) }])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-background via-background to-muted/20">
      {/* Animated gradient orbs */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-0 left-1/4 w-96 h-96 bg-primary/10 rounded-full blur-3xl animate-pulse-glow" />
        <div
          className="absolute bottom-0 right-1/4 w-96 h-96 bg-accent/10 rounded-full blur-3xl animate-pulse-glow"
          style={{ animationDelay: "1.5s" }}
        />
      </div>

      <div className="relative z-10">
        <Header walletAddress={wallet?.address} />

        <div className="w-full px-4 sm:px-6 lg:px-8 py-4">
          {/* 3/4 main UI (left) and 1/4 timeline (right) */}
          <div className="grid grid-cols-1 lg:grid-cols-[minmax(0,2.5fr)_minmax(360px,480px)] gap-6 items-start">
            <div className="flex flex-col gap-6 min-w-0">
              <div className="flex items-center gap-3 flex-wrap">
                <StatusBadge statusCode={statusCode} loading={loading} />
                <div className="flex items-center gap-2 px-4 py-2 rounded-lg border border-border bg-card/50 backdrop-blur-sm text-sm">
                  <div className="w-2 h-2 rounded-full bg-accent animate-pulse" />
                  <span className="text-muted-foreground">API:</span>
                  <span className="font-mono text-foreground">localhost:8000</span>
                </div>
              </div>

              <div className="grid gap-6 lg:grid-cols-2">
                <ApiEndpoint
                  method="POST"
                  path="/summarize/logs"
                  title="Summarize Logs"
                  description="Analyze plain text logs"
                  onSubmit={handleRequest}
                  type="text"
                />

                <ApiEndpoint
                  method="POST"
                  path="/clean/dataframe"
                  title="Clean DataFrame (JSON)"
                  description="JSON body with rules"
                  onSubmit={handleRequest}
                  type="json"
                />

                <ApiEndpoint
                  method="POST"
                  path="/clean/dataframe"
                  title="Clean DataFrame (CSV)"
                  description="Upload CSV with optional rules"
                  onSubmit={handleRequest}
                  type="csv"
                />

                <ApiEndpoint
                  method="POST"
                  path="/extract/pdf"
                  title="Extract PDF"
                  description="Upload PDF and choose extraction mode"
                  onSubmit={handleRequest}
                  type="pdf"
                />
              </div>

              <ApiEndpoint
                method="POST"
                path="/validate/csv"
                title="Validate CSV (Advanced)"
                description="Upload CSV and build comprehensive validation config"
                onSubmit={handleRequest}
                type="validate"
                fullWidth
              />

              <ResultsPanel
                responseHeaders={responseHeaders}
                responseBody={responseBody}
                errorCount={errorCount}
                warningCount={warningCount}
                errors={errors}
                lastValidationResult={lastValidationResult}
                lastCsv={lastCsv}
              />
            </div>

            <div className="w-full rounded-xl border border-border bg-card/90 backdrop-blur-md shadow-xl p-5 space-y-3 lg:sticky lg:top-36 lg:ml-auto max-w-full">
              <div className="text-sm font-semibold text-foreground">Wallet Handshake Timeline</div>
              <div className="space-y-3 font-mono text-xs leading-relaxed max-h-[420px] overflow-y-auto overflow-x-auto bg-black/60 p-4 rounded-lg border border-border/70">
                {timeline.length === 0 ? (
                  <div className="text-muted-foreground">No events yet</div>
                ) : (
                  timeline.map((evt, idx) => {
                    const is402 = evt.status === 402
                    const is200 = evt.status !== undefined && evt.status >= 200 && evt.status < 300
                    const labelColor = is402 ? "text-red-400" : is200 ? "text-emerald-400" : "text-foreground"
                    return (
                      <div key={idx} className="border-b border-border/60 pb-2 last:border-b-0 last:pb-0 space-y-1">
                        <div className={`flex items-center gap-2 ${labelColor}`}>
                          <span className="text-muted-foreground shrink-0">{`[${idx + 1}]`}</span>
                          <span className="font-semibold">{evt.label}</span>
                        </div>
                        {evt.detail && (
                          <pre className="text-foreground whitespace-pre-wrap break-all text-xs">{evt.detail}</pre>
                        )}
                      </div>
                    )
                  })
                )}
              </div>
            </div>
          </div>
        </div>
        <div className="fixed bottom-6 right-6 z-40">
          <div className="min-w-[240px] rounded-2xl border border-border bg-card/90 backdrop-blur shadow-xl px-6 py-4 text-base flex flex-col gap-2">
            <div className="flex items-center justify-between">
              <span className="px-3 py-1 rounded-md bg-primary/10 text-primary font-semibold text-xs uppercase tracking-wide">Requests</span>
              <span className="font-semibold text-foreground text-lg">{requestCount}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="px-3 py-1 rounded-md bg-emerald-500/10 text-emerald-300 font-semibold text-xs uppercase tracking-wide">Total</span>
              <span className="font-semibold text-foreground text-lg">${totalSpent.toFixed(2)}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
