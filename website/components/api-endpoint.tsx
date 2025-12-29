"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Checkbox } from "@/components/ui/checkbox"
import { Send } from "lucide-react"
import { cn } from "@/lib/utils"

interface ApiEndpointProps {
  method: string
  path: string
  title: string
  description: string
  onSubmit: (path: string, options: RequestInit) => Promise<void>
  type: "text" | "json" | "csv" | "pdf" | "validate"
  fullWidth?: boolean
}

export function ApiEndpoint({ method, path, title, description, onSubmit, type, fullWidth = false }: ApiEndpointProps) {
  const [textInput, setTextInput] = useState(
    type === "text"
      ? "ERROR db timeout\nERROR db timeout\nWARN cache miss"
      : type === "json"
        ? JSON.stringify(
            {
              data: [
                { name: " Alice ", age: "30", city: "nyc" },
                { name: "Bob", age: "thirty", city: "NYC" },
                { name: "Alice", age: "30", city: "nyc" },
              ],
              rules: {
                normalize_columns: true,
                trim_strings: true,
                deduplicate: true,
                coerce_types: { age: "int" },
              },
            },
            null,
            2,
          )
        : "",
  )
  const [file, setFile] = useState<File | null>(null)
  const [csvRules, setCsvRules] = useState("")
  const [pdfMode, setPdfMode] = useState("text")

  // Validation config states
  const [stripWhitespace, setStripWhitespace] = useState(true)
  const [noEmptyHeaders, setNoEmptyHeaders] = useState(true)
  const [noEmptyRows, setNoEmptyRows] = useState(true)
  const [noEmptyCells, setNoEmptyCells] = useState(false)
  const [noNegatives, setNoNegatives] = useState(false)
  const [includeCsv, setIncludeCsv] = useState(false)
  const [maxRows, setMaxRows] = useState("50000")
  const [maxCols, setMaxCols] = useState("200")

  // Clean CSV rule toggles
  const [cleanNormalize, setCleanNormalize] = useState(true)
  const [cleanTrim, setCleanTrim] = useState(true)
  const [cleanDropEmptyRows, setCleanDropEmptyRows] = useState(true)
  const [cleanDedupe, setCleanDedupe] = useState(true)
  const [cleanNoNegatives, setCleanNoNegatives] = useState(false)
  const [cleanNegativeCols, setCleanNegativeCols] = useState("")
  const [cleanIncludeCsv, setCleanIncludeCsv] = useState(false)

  const handleSubmit = async () => {
    if (type === "text") {
      await onSubmit(path, {
        method,
        headers: { "Content-Type": "text/plain" },
        body: textInput,
      })
    } else if (type === "json") {
      await onSubmit(path, {
        method,
        headers: { "Content-Type": "application/json" },
        body: textInput,
      })
    } else if (type === "csv") {
      if (!file) {
        alert("Please select a CSV file")
        return
      }
      const formData = new FormData()
      formData.append("file", file)
      const rules: Record<string, any> = {
        normalize_columns: cleanNormalize,
        trim_strings: cleanTrim,
        drop_empty_rows: cleanDropEmptyRows,
        deduplicate: cleanDedupe,
        remove_negative_rows: cleanNoNegatives,
      }
      const negCols = cleanNegativeCols
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean)
      if (negCols.length) {
        rules.negative_columns = negCols
      }
      if (csvRules.trim()) {
        try {
          const extra = JSON.parse(csvRules)
          Object.assign(rules, extra)
        } catch {
          alert("Invalid rules JSON")
          return
        }
      }
      if (cleanIncludeCsv) {
        formData.append("include_csv", "true")
      }
      formData.append("rules", JSON.stringify(rules))
      await onSubmit(path, { method, body: formData })
    } else if (type === "pdf") {
      if (!file) {
        alert("Please select a PDF file")
        return
      }
      const formData = new FormData()
      formData.append("file", file)
      formData.append("mode", pdfMode)
      await onSubmit(path, { method, body: formData })
    } else if (type === "validate") {
      if (!file) {
        alert("Please select a CSV file")
        return
      }
      const config = {
        strip_whitespace: stripWhitespace,
        no_empty_headers: noEmptyHeaders,
        no_empty_rows: noEmptyRows,
        no_empty_cells: noEmptyCells,
        no_negative_numbers: noNegatives,
        max_rows: Number.parseInt(maxRows) || 50000,
        max_cols: Number.parseInt(maxCols) || 200,
      }
      const formData = new FormData()
      formData.append("file", file)
      formData.append("config", JSON.stringify(config))
      await onSubmit(path, { method, body: formData })
    }
  }

  return (
    <div className={cn("group", fullWidth && "lg:col-span-2")}>
      <div className="h-full flex flex-col rounded-2xl border border-border bg-card/50 backdrop-blur-sm p-6 hover:bg-card transition-all duration-300 hover:shadow-lg hover:shadow-primary/5">
        <div className="flex items-start justify-between mb-4">
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-2">
              <span className="px-2 py-0.5 rounded-md bg-accent/20 text-accent text-xs font-bold uppercase tracking-wider">
                {method}
              </span>
              <code className="text-xs text-muted-foreground font-mono">{path}</code>
              <span className="px-2 py-0.5 rounded-md bg-primary/20 text-primary text-xs font-semibold">
                {path === "/validate/csv"
                  ? "$0.01"
                  : path === "/clean/dataframe"
                    ? "$0.05"
                    : path === "/extract/pdf"
                      ? "$0.05"
                      : "$0.02"}
              </span>
            </div>
            <h3 className="text-lg font-semibold mb-1 text-balance">{title}</h3>
            <p className="text-sm text-muted-foreground text-pretty">{description}</p>
          </div>
        </div>

        <div className="space-y-4 flex-1">
          {(type === "text" || type === "json") && (
            <div>
              <Label className="text-xs uppercase tracking-wider text-muted-foreground mb-2 block">
                {type === "text" ? "Log Input" : "JSON Payload"}
              </Label>
              <Textarea
                value={textInput}
                onChange={(e) => setTextInput(e.target.value)}
                rows={type === "json" ? 10 : 5}
                className="font-mono text-sm bg-muted/50 resize-none"
              />
            </div>
          )}

          {type === "csv" && (
            <>
              <div>
                <Label className="text-xs uppercase tracking-wider text-muted-foreground mb-2 block">CSV File</Label>
                <Input
                  type="file"
                  accept=".csv"
                  onChange={(e) => setFile(e.target.files?.[0] || null)}
                  className="bg-muted/50"
                />
              </div>
              <div>
                <Label className="text-xs uppercase tracking-wider text-muted-foreground mb-2 block">Quick Rules</Label>
                <div className="grid grid-cols-2 gap-2 text-sm">
                  {[
                    { label: "Normalize columns", checked: cleanNormalize, onChange: setCleanNormalize },
                    { label: "Trim strings", checked: cleanTrim, onChange: setCleanTrim },
                    { label: "Drop empty rows", checked: cleanDropEmptyRows, onChange: setCleanDropEmptyRows },
                    { label: "Deduplicate rows", checked: cleanDedupe, onChange: setCleanDedupe },
                    { label: "Remove negative rows", checked: cleanNoNegatives, onChange: setCleanNoNegatives },
                    { label: "Include downloadable CSV", checked: cleanIncludeCsv, onChange: setCleanIncludeCsv },
                  ].map(({ label, checked, onChange }) => (
                    <div key={label} className="flex items-center gap-2">
                      <Checkbox checked={checked} onCheckedChange={(v) => onChange(Boolean(v))} />
                      <label className="text-sm cursor-pointer">{label}</label>
                    </div>
                  ))}
                </div>
              <div className="mt-4">
                <Label className="text-xs uppercase tracking-wider text-muted-foreground mb-2 block">
                  Negative check columns (comma-separated)
                </Label>
                <Input
                  value={cleanNegativeCols}
                  onChange={(e) => setCleanNegativeCols(e.target.value)}
                  className="bg-muted/50"
                  placeholder="price,amount"
                />
              </div>
              </div>
              <div>
                <Label className="text-xs uppercase tracking-wider text-muted-foreground mb-2 block">
                  Rules JSON (optional)
                </Label>
                <Textarea
                  value={csvRules}
                  onChange={(e) => setCsvRules(e.target.value)}
                  rows={3}
                  placeholder='{"trim_strings": true, "deduplicate": true}'
                  className="font-mono text-sm bg-muted/50"
                />
              </div>
            </>
          )}

          {type === "pdf" && (
            <>
              <div>
                <Label className="text-xs uppercase tracking-wider text-muted-foreground mb-2 block">PDF File</Label>
                <Input
                  type="file"
                  accept=".pdf"
                  onChange={(e) => setFile(e.target.files?.[0] || null)}
                  className="bg-muted/50"
                />
              </div>
              <div>
                <Label className="text-xs uppercase tracking-wider text-muted-foreground mb-2 block">
                  Extraction Mode
                </Label>
                <Select value={pdfMode} onValueChange={setPdfMode}>
                  <SelectTrigger className="bg-muted/50">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="text">Text</SelectItem>
                    <SelectItem value="tables">Tables</SelectItem>
                    <SelectItem value="both">Both</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </>
          )}

          {type === "validate" && (
            <>
              <div>
                <Label className="text-xs uppercase tracking-wider text-muted-foreground mb-2 block">CSV File</Label>
                <Input
                  type="file"
                  accept=".csv"
                  onChange={(e) => setFile(e.target.files?.[0] || null)}
                  className="bg-muted/50"
                />
              </div>
              <div className="grid sm:grid-cols-2 gap-4">
                <div className="space-y-3">
                  <Label className="text-xs uppercase tracking-wider text-muted-foreground">Options</Label>
                  {[
                    { label: "Strip whitespace", checked: stripWhitespace, onChange: setStripWhitespace },
                    { label: "No empty headers", checked: noEmptyHeaders, onChange: setNoEmptyHeaders },
                    { label: "No empty rows", checked: noEmptyRows, onChange: setNoEmptyRows },
                    { label: "No empty cells", checked: noEmptyCells, onChange: setNoEmptyCells },
                    { label: "Check for negative numbers", checked: noNegatives, onChange: setNoNegatives },
                  ].map(({ label, checked, onChange }) => (
                    <div key={label} className="flex items-center gap-2">
                      <Checkbox
                        checked={checked}
                        onCheckedChange={(v) => onChange(Boolean(v))}
                      />
                      <label className="text-sm cursor-pointer">{label}</label>
                    </div>
                  ))}
                </div>
                <div className="space-y-3">
                  <Label className="text-xs uppercase tracking-wider text-muted-foreground">Limits</Label>
                  <div>
                    <Label className="text-xs text-muted-foreground mb-1 block">Max Rows</Label>
                    <Input value={maxRows} onChange={(e) => setMaxRows(e.target.value)} className="bg-muted/50" />
                  </div>
                  <div>
                    <Label className="text-xs text-muted-foreground mb-1 block">Max Columns</Label>
                    <Input value={maxCols} onChange={(e) => setMaxCols(e.target.value)} className="bg-muted/50" />
                  </div>
                </div>
              </div>
            </>
          )}

          <Button
            onClick={handleSubmit}
            className="w-full bg-gradient-to-r from-primary to-accent hover:opacity-90 transition-opacity group mt-auto"
            size="lg"
          >
            <Send className="w-4 h-4 mr-2 group-hover:translate-x-0.5 transition-transform" />
            Send Request
          </Button>
        </div>
      </div>
    </div>
  )
}
