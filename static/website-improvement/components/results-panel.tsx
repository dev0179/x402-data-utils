"use client"

import { Button } from "@/components/ui/button"
import { Download } from "lucide-react"

interface ResultsPanelProps {
  responseHeaders: Record<string, string>
  responseBody: any
  errorCount: number
  warningCount: number
  errors: any[]
  lastValidationResult: any
  lastCsv: string | null
}

export function ResultsPanel({
  responseHeaders,
  responseBody,
  errorCount,
  warningCount,
  errors,
  lastValidationResult,
  lastCsv,
}: ResultsPanelProps) {
  const downloadReport = () => {
    if (!lastValidationResult) return
    const blob = new Blob([JSON.stringify(lastValidationResult, null, 2)], {
      type: "application/json",
    })
    const url = URL.createObjectURL(blob)
    const a = document.createElement("a")
    a.href = url
    a.download = "validation-report.json"
    a.click()
    URL.revokeObjectURL(url)
  }

  const downloadCsv = () => {
    if (!lastCsv) return
    const blob = new Blob([lastCsv], { type: "text/csv" })
    const url = URL.createObjectURL(blob)
    const a = document.createElement("a")
    a.href = url
    a.download = "validated.csv"
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="mt-8 rounded-2xl border border-border bg-card/50 backdrop-blur-sm p-6">
      <h2 className="text-xl font-semibold mb-6 text-balance">Response & Evidence</h2>

      <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        {[
          { label: "X-X402-Price", value: responseHeaders["x-x402-price"] },
          { label: "X-X402-PayTo", value: responseHeaders["x-x402-payto"] },
          { label: "X-X402-Path", value: responseHeaders["x-x402-path"] },
          { label: "X-X402-Mock-Settled", value: responseHeaders["x-x402-mock-settled"] },
        ].map(({ label, value }) => (
          <div key={label}>
            <div className="text-xs uppercase tracking-wider text-muted-foreground mb-2">{label}</div>
            <div className="rounded-lg border border-border bg-muted/50 px-3 py-2 font-mono text-sm break-all">
              {value || "-"}
            </div>
          </div>
        ))}
      </div>

      <div className="mb-6">
        <div className="text-xs uppercase tracking-wider text-muted-foreground mb-2">Response Body</div>
        <div className="rounded-lg border border-border bg-muted/50 p-4 font-mono text-xs overflow-x-auto max-h-80 overflow-y-auto">
          <pre>{responseBody ? JSON.stringify(responseBody, null, 2) : "-"}</pre>
        </div>
      </div>

      {(lastValidationResult || lastCsv) && (
        <>
          <div className="flex items-center justify-between mb-4">
            <div className="flex gap-4">
              {lastValidationResult && (
                <>
                  <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg border border-destructive/50 bg-destructive/10">
                    <span className="text-xs font-semibold text-destructive">Errors: {errorCount}</span>
                  </div>
                  <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg border border-accent/50 bg-accent/10">
                    <span className="text-xs font-semibold text-accent">Warnings: {warningCount}</span>
                  </div>
                </>
              )}
            </div>
            <div className="flex gap-2">
              <Button onClick={downloadReport} variant="outline" size="sm" disabled={!lastValidationResult}>
                <Download className="w-4 h-4 mr-2" />
                Download Report
              </Button>
              <Button onClick={downloadCsv} variant="outline" size="sm" disabled={!lastCsv}>
                <Download className="w-4 h-4 mr-2" />
                Download CSV
              </Button>
            </div>
          </div>

          {lastValidationResult && errors.length > 0 && (
            <div>
              <div className="text-xs uppercase tracking-wider text-muted-foreground mb-2">Top 20 Errors</div>
              <div className="rounded-lg border border-border overflow-hidden">
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead className="bg-muted/50 border-b border-border">
                      <tr>
                        <th className="px-4 py-2 text-left font-semibold">Row</th>
                        <th className="px-4 py-2 text-left font-semibold">Column</th>
                        <th className="px-4 py-2 text-left font-semibold">Code</th>
                        <th className="px-4 py-2 text-left font-semibold">Message</th>
                        <th className="px-4 py-2 text-left font-semibold">Value</th>
                      </tr>
                    </thead>
                    <tbody>
                      {errors.map((error, idx) => (
                        <tr key={idx} className="border-b border-border last:border-0 hover:bg-muted/30">
                          <td className="px-4 py-2">{error.row || "-"}</td>
                          <td className="px-4 py-2 font-mono">{error.column || "-"}</td>
                          <td className="px-4 py-2">
                            <span className="px-2 py-0.5 rounded-md bg-destructive/20 text-destructive text-xs font-mono">
                              {error.code || "-"}
                            </span>
                          </td>
                          <td className="px-4 py-2 text-muted-foreground">{error.message || "-"}</td>
                          <td className="px-4 py-2 font-mono text-xs">{String(error.value || "-")}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  )
}
