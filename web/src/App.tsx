import React, { useState, useEffect } from "react"
import { 
  Download, 
  FolderOpen, 
  Sparkles, 
  Clock, 
  Flame, 
  CheckCircle2, 
  AlertCircle, 
  Loader2, 
  Copy, 
  Check, 
  Scissors, 
  Video, 
  Laptop
} from "lucide-react"

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Progress } from "@/components/ui/progress"

interface HighlightItem {
  title: string
  start_time: string
  end_time: string
  duration_seconds: number
  virality_score: number
  hook_text: string
  reason: string
}

interface ClipItem {
  clip_index: number
  title: string
  start_time: string
  end_time: string
  duration_seconds: number
  virality_score: number
  hook_text: string
  reason: string
  video_url: string
  thumbnail_url?: string
  filename: string
  file_size_mb: number
}

interface JobStatus {
  job_id: string
  url: string
  status: "pending" | "processing" | "completed" | "failed"
  progress: number
  current_step: string
  title?: string
  summary?: string
  highlights: HighlightItem[]
  clips: ClipItem[]
  error?: string
}

export function App() {
  const [url, setUrl] = useState("")
  const [resolution, setResolution] = useState(720)
  const [jobId, setJobId] = useState<string | null>(null)
  const [job, setJob] = useState<JobStatus | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [copiedHook, setCopiedHook] = useState<string | null>(null)

  // Poll job status every 1.5 seconds if processing
  useEffect(() => {
    if (!jobId) return

    const interval = setInterval(async () => {
      try {
        const res = await fetch(`/api/status/${jobId}`)
        if (res.ok) {
          const data: JobStatus = await res.json()
          setJob(data)
          if (data.status === "completed" || data.status === "failed") {
            clearInterval(interval)
            setIsSubmitting(false)
          }
        }
      } catch (e) {
        console.error("Status fetch failed", e)
      }
    }, 1500)

    return () => clearInterval(interval)
  }, [jobId])

  const handleStartProcess = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!url.trim()) return

    setIsSubmitting(true)
    setJob(null)

    try {
      const res = await fetch("/api/process", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url: url.trim(), resolution })
      })

      if (!res.ok) {
        const err = await res.json()
        alert(err.detail || "Gagal memproses video")
        setIsSubmitting(false)
        return
      }

      const data = await res.json()
      setJobId(data.job_id)
    } catch (e: any) {
      alert("Koneksi ke backend gagal: " + e.message)
      setIsSubmitting(false)
    }
  }

  const handleOpenFolder = async () => {
    try {
      await fetch("/api/open-output-folder", { method: "POST" })
    } catch (e) {
      alert("Tidak dapat membuka folder output.")
    }
  }

  const copyToClipboard = (text: string, id: string) => {
    navigator.clipboard.writeText(text)
    setCopiedHook(id)
    setTimeout(() => setCopiedHook(null), 2000)
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans selection:bg-rose-500 selection:text-white">
      {/* Top Navigation */}
      <header className="border-b border-slate-800 bg-slate-900/60 backdrop-blur-md sticky top-0 z-50">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-rose-500 to-amber-500 flex items-center justify-center shadow-lg shadow-rose-500/20">
              <Scissors className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 className="font-bold text-lg leading-tight tracking-tight flex items-center gap-2">
                Auto-Clipper <span className="text-xs bg-rose-500/20 text-rose-300 border border-rose-500/30 px-2 py-0.5 rounded-full font-medium">Smart AI</span>
              </h1>
              <p className="text-xs text-slate-400">YouTube Highlight Extractor & CapCut Pro Workflow</p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <Badge variant="outline" className="hidden sm:flex items-center gap-1.5 border-slate-700 bg-slate-800/80 text-emerald-400 text-xs py-1">
              <Laptop className="w-3.5 h-3.5" />
              Laptop Local Engine (Bebas 403)
            </Badge>

            <Button 
              variant="outline" 
              size="sm" 
              onClick={handleOpenFolder}
              className="border-slate-700 hover:bg-slate-800 text-slate-200 flex items-center gap-2 text-xs"
            >
              <FolderOpen className="w-4 h-4 text-amber-400" />
              <span className="hidden md:inline">Buka Folder Output</span>
            </Button>
          </div>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 max-w-6xl w-full mx-auto px-4 sm:px-6 py-8 space-y-8">
        
        {/* Hero & Input Card */}
        <Card className="bg-slate-900 border-slate-800 shadow-xl overflow-hidden relative">
          <div className="absolute top-0 right-0 w-96 h-96 bg-rose-500/5 rounded-full blur-3xl pointer-events-none" />
          <div className="absolute bottom-0 left-0 w-96 h-96 bg-amber-500/5 rounded-full blur-3xl pointer-events-none" />
          
          <CardHeader className="pb-4">
            <CardTitle className="text-xl sm:text-2xl font-bold flex items-center gap-2">
              <Sparkles className="w-6 h-6 text-rose-400" />
              Otomasi Pemotongan Klip Viral
            </CardTitle>
            <CardDescription className="text-slate-400 text-sm">
              Tempelkan URL video YouTube (Podcast, Edukasi, Wawancara). AI Gemini akan mencari 1-3 momen paling engaging (30–90s) dan memotongnya secara otomatis.
            </CardDescription>
          </CardHeader>

          <CardContent>
            <form onSubmit={handleStartProcess} className="space-y-4">
              <div className="flex flex-col md:flex-row gap-3">
                <div className="relative flex-1">
                  <Input
                    type="url"
                    required
                    placeholder="https://www.youtube.com/watch?v=... atau https://youtu.be/..."
                    value={url}
                    onChange={(e) => setUrl(e.target.value)}
                    disabled={isSubmitting}
                    className="bg-slate-950 border-slate-700 text-white placeholder:text-slate-500 h-12 px-4 focus-visible:ring-rose-500"
                  />
                </div>

                <div className="flex gap-2">
                  <select 
                    value={resolution}
                    onChange={(e) => setResolution(Number(e.target.value))}
                    disabled={isSubmitting}
                    className="bg-slate-950 border border-slate-700 text-slate-200 text-sm rounded-md px-3 h-12 focus:ring-rose-500 focus:outline-none"
                  >
                    <option value={720}>720p HD (Optimal)</option>
                    <option value={480}>480p SD (Lebih Cepat)</option>
                    <option value={1080}>1080p FHD (Tinggi)</option>
                  </select>

                  <Button 
                    type="submit" 
                    disabled={isSubmitting || !url.trim()}
                    className="bg-gradient-to-r from-rose-500 to-rose-600 hover:from-rose-600 hover:to-rose-700 text-white font-medium h-12 px-6 shadow-lg shadow-rose-500/25 flex items-center gap-2 shrink-0"
                  >
                    {isSubmitting ? (
                      <>
                        <Loader2 className="w-4 h-4 animate-spin" />
                        <span>Memproses...</span>
                      </>
                    ) : (
                      <>
                        <Scissors className="w-4 h-4" />
                        <span>Mulai Ekstrak Klip</span>
                      </>
                    )}
                  </Button>
                </div>
              </div>

              {/* Example Links */}
              <div className="flex flex-wrap items-center gap-2 pt-1 text-xs text-slate-400">
                <span className="text-slate-500">Contoh Coba:</span>
                <button
                  type="button"
                  onClick={() => setUrl("https://youtu.be/mlFQ2OlWRSU")}
                  className="hover:text-rose-400 underline decoration-slate-600 underline-offset-4 transition"
                >
                  Prof. Stella Christie (Helmy Yahya)
                </button>
                <span>•</span>
                <button
                  type="button"
                  onClick={() => setUrl("https://youtu.be/vhahqGkXR1U")}
                  className="hover:text-rose-400 underline decoration-slate-600 underline-offset-4 transition"
                >
                  Neuroscientist #85
                </button>
              </div>
            </form>
          </CardContent>
        </Card>

        {/* Progress Card when Active */}
        {job && (
          <Card className="bg-slate-900/90 border-slate-800 shadow-xl overflow-hidden">
            <CardHeader className="pb-3 border-b border-slate-800/80">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  {job.status === "processing" && <Loader2 className="w-5 h-5 text-rose-400 animate-spin" />}
                  {job.status === "completed" && <CheckCircle2 className="w-5 h-5 text-emerald-400" />}
                  {job.status === "failed" && <AlertCircle className="w-5 h-5 text-rose-500" />}
                  <h3 className="font-semibold text-slate-200">
                    {job.title || "Memproses Permintaan Video..."}
                  </h3>
                </div>

                <Badge 
                  className={`capitalize text-xs px-2.5 py-0.5 ${
                    job.status === "completed" 
                      ? "bg-emerald-500/20 text-emerald-300 border-emerald-500/30" 
                      : job.status === "failed"
                      ? "bg-rose-500/20 text-rose-300 border-rose-500/30"
                      : "bg-amber-500/20 text-amber-300 border-amber-500/30"
                  }`}
                >
                  {job.status} ({job.progress}%)
                </Badge>
              </div>
            </CardHeader>

            <CardContent className="pt-5 space-y-4">
              <div className="space-y-2">
                <div className="flex justify-between text-xs text-slate-400">
                  <span className="font-medium text-slate-300 flex items-center gap-1.5">
                    {job.current_step}
                  </span>
                  <span>{job.progress}%</span>
                </div>
                <Progress value={job.progress} className="h-2 bg-slate-950" />
              </div>

              {job.error && (
                <div className="p-4 rounded-lg bg-rose-950/40 border border-rose-800/60 text-rose-300 text-sm flex gap-3 items-start">
                  <AlertCircle className="w-5 h-5 shrink-0 mt-0.5 text-rose-400" />
                  <div>
                    <p className="font-semibold">Terjadi Kendala:</p>
                    <p className="text-xs text-rose-300/90 mt-1 font-mono">{job.error}</p>
                  </div>
                </div>
              )}

              {/* Video Summary */}
              {job.summary && (
                <div className="p-4 rounded-lg bg-slate-950/80 border border-slate-800/80 space-y-2">
                  <div className="flex items-center gap-2 text-xs font-semibold text-amber-400 uppercase tracking-wider">
                    <Sparkles className="w-3.5 h-3.5" />
                    Ringkasan Konten oleh Gemini AI
                  </div>
                  <p className="text-sm text-slate-300 leading-relaxed">{job.summary}</p>
                </div>
              )}
            </CardContent>
          </Card>
        )}

        {/* Results Section: Generated Clips */}
        {job && job.clips && job.clips.length > 0 && (
          <div className="space-y-6 pt-4">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-xl font-bold text-white flex items-center gap-2">
                  <Video className="w-5 h-5 text-rose-400" />
                  Hasil Klip Highlight ({job.clips.length} Video)
                </h2>
                <p className="text-xs text-slate-400 mt-0.5">
                  Siap diunduh atau langsung diimpor ke CapCut Pro untuk dijadikan format vertikal 9:16 + auto-caption.
                </p>
              </div>

              <Button
                variant="outline"
                size="sm"
                onClick={handleOpenFolder}
                className="border-slate-700 bg-slate-900 hover:bg-slate-800 text-xs flex items-center gap-2"
              >
                <FolderOpen className="w-4 h-4 text-amber-400" />
                Buka di File Explorer
              </Button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {job.clips.map((clip) => (
                <Card key={clip.clip_index} className="bg-slate-900 border-slate-800 flex flex-col overflow-hidden hover:border-slate-700 transition shadow-lg">
                  {/* Built-in Video Player Preview */}
                  <div className="relative bg-black aspect-video flex items-center justify-center overflow-hidden border-b border-slate-800">
                    <video
                      controls
                      preload="metadata"
                      poster={clip.thumbnail_url || undefined}
                      src={clip.video_url}
                      className="w-full h-full object-contain"
                    />
                  </div>

                  <CardHeader className="pb-3 pt-4">
                    <div className="flex items-start justify-between gap-2">
                      <Badge className="bg-rose-500/20 text-rose-300 border-rose-500/30 text-xs">
                        Klip #{clip.clip_index}
                      </Badge>
                      
                      <div className="flex items-center gap-1.5 text-xs font-semibold text-amber-400 bg-amber-500/10 px-2 py-0.5 rounded border border-amber-500/20">
                        <Flame className="w-3.5 h-3.5 fill-amber-400 text-amber-400" />
                        <span>{clip.virality_score}/10</span>
                      </div>
                    </div>

                    <CardTitle className="text-base font-bold text-white mt-2 line-clamp-2">
                      {clip.title}
                    </CardTitle>

                    <div className="flex items-center gap-3 text-xs text-slate-400 mt-1">
                      <span className="flex items-center gap-1 font-mono">
                        <Clock className="w-3.5 h-3.5 text-slate-500" />
                        {clip.start_time} - {clip.end_time}
                      </span>
                      <span>•</span>
                      <span>{Math.round(clip.duration_seconds)}s</span>
                      <span>•</span>
                      <span>{clip.file_size_mb} MB</span>
                    </div>
                  </CardHeader>

                  <CardContent className="space-y-3 flex-1 text-xs">
                    {/* 3-Second Hook */}
                    <div className="p-2.5 rounded bg-slate-950 border border-slate-800">
                      <div className="flex items-center justify-between text-slate-400 font-medium mb-1">
                        <span>🪝 Hook 3 Detik:</span>
                        <button
                          type="button"
                          onClick={() => copyToClipboard(clip.hook_text, `hook-${clip.clip_index}`)}
                          className="hover:text-white flex items-center gap-1 transition"
                        >
                          {copiedHook === `hook-${clip.clip_index}` ? (
                            <Check className="w-3.5 h-3.5 text-emerald-400" />
                          ) : (
                            <Copy className="w-3.5 h-3.5" />
                          )}
                        </button>
                      </div>
                      <p className="italic text-slate-200 line-clamp-2">&quot;{clip.hook_text}&quot;</p>
                    </div>

                    {/* AI Reason */}
                    <p className="text-slate-400 text-xs leading-relaxed line-clamp-3">
                      <span className="text-slate-300 font-medium">Alasan Viral:</span> {clip.reason}
                    </p>
                  </CardContent>

                  <CardFooter className="pt-3 border-t border-slate-800/80 flex gap-2">
                    <a
                      href={clip.video_url}
                      download={clip.filename}
                      className="flex-1"
                    >
                      <Button variant="default" className="w-full bg-slate-800 hover:bg-slate-700 text-white text-xs h-9 flex items-center gap-2">
                        <Download className="w-3.5 h-3.5" />
                        Download MP4
                      </Button>
                    </a>
                  </CardFooter>
                </Card>
              ))}
            </div>
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-900 bg-slate-950 py-6 text-center text-xs text-slate-500">
        <p>Auto-Clipper & Smart Summarizer Bot • Local Windows Engine with Gemini 3.5 & CapCut Pro Workflow</p>
      </footer>
    </div>
  )
}

export default App
