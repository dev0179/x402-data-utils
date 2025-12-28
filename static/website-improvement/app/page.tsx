"use client"

import { useState } from "react"
import { Header } from "@/components/header"
import { ApiEndpoint } from "@/components/api-endpoint"
import { ResultsPanel } from "@/components/results-panel"
import { StatusBadge } from "@/components/status-badge"

export default function Home() {
  const [isPaid, setIsPaid] = useState(false)
  const [statusCode, setStatusCode] = useState<number | null>(null)
  const [loading, setLoading] = useState(false)
  const [responseHeaders, setResponseHeaders] = useState<Record<string, string>>({})
  const [responseBody, setResponseBody] = useState<any>(null)
  const [errorCount, setErrorCount] = useState<number>(0)
  const [warningCount, setWarningCount] = useState<number>(0)
  const [errors, setErrors] = useState<any[]>([])
  const [lastValidationResult, setLastValidationResult] = useState<any>(null)
  const [lastCsv, setLastCsv] = useState<string | null>(null)
  const [timeline, setTimeline] = useState<{ label: string; detail: string }[]>([])

  const handleRequest = async (path: string, options: RequestInit) => {
    setLoading(true)
    setStatusCode(null)

    const headers = new Headers(options.headers)
    const events: { label: string; detail: string }[] = []

    try {
      events.push({ label: `Sent ${options.method || "POST"}`, detail: path })

      let res = await fetch(`http://localhost:8000${path}`, {
        ...options,
        headers,
      })
      let contentType = res.headers.get("content-type") || ""
      let body = contentType.includes("application/json") ? await res.json() : await res.text()

      // If 402, show payment info and retry automatically
      if (res.status === 402) {
        const price = res.headers.get("x-x402-price") || (body && body.price)
        const payTo = res.headers.get("x-x402-payto") || (body && body.pay_to)
        events.push({ label: "Received 402", detail: `price=${price || "-"} pay_to=${payTo || "-"}` })
        // auto-retry with mock proof
        headers.set("X-X402-Mock-Paid", "true")
        events.push({ label: "Retrying", detail: "with X-X402-Mock-Paid:true" })
        res = await fetch(`http://localhost:8000${path}`, {
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
      const settled = res.headers.get("x-x402-mock-settled")
      events.push({ label: `Received ${res.status}`, detail: `settled=${settled || false}` })
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
        <Header isPaid={isPaid} setIsPaid={setIsPaid} timeline={timeline} />

        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex flex-col gap-6">
          <div className="flex items-center gap-4">
            <StatusBadge statusCode={statusCode} loading={loading} />
            <div className="flex items-center gap-2 px-4 py-2 rounded-lg border border-border bg-card/50 backdrop-blur-sm text-sm">
              <div className="w-2 h-2 rounded-full bg-accent animate-pulse" />
              <span className="text-muted-foreground">API:</span>
              <span className="font-mono text-foreground">localhost:8000</span>
            </div>
          </div>

          <div className="grid gap-6 lg:grid-cols-2 mb-8">
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
      </div>
    </div>
  )
}
