import { useState, useEffect, useRef, useCallback } from 'react'
import { FFmpeg } from '@ffmpeg/ffmpeg'
import { fetchFile, toBlobURL } from '@ffmpeg/util'

const ffmpegInstance = new FFmpeg()

// Files above this threshold are processed via byte-streaming (no WASM memory needed)
const STREAM_THRESHOLD_BYTES = 300 * 1024 * 1024 // 300 MB

function formatSize(bytes) {
  if (bytes >= 1024 * 1024 * 1024)
    return `${(bytes / 1024 / 1024 / 1024).toFixed(2)} GB`
  return `${(bytes / 1024 / 1024).toFixed(0)} MB`
}

function App() {
  const [ffmpegLoaded, setFfmpegLoaded]   = useState(false)
  const [ffmpegLoading, setFfmpegLoading] = useState(false)
  const [loadError, setLoadError]         = useState(null)

  const [file, setFile]         = useState(null)
  const [numParts, setNumParts] = useState(2)
  const [overlap, setOverlap]   = useState(5.0)

  const [isRunning, setIsRunning]   = useState(false)
  const [status, setStatus]         = useState('ČEKÁM NA ENGINE...')
  const [progress, setProgress]     = useState(0)
  const [logs, setLogs]             = useState(['> SYSTEM READY.'])
  const [outputFiles, setOutputFiles] = useState([])
  const [isDragging, setIsDragging] = useState(false)

  const terminalRef = useRef(null)
  const fileInputRef = useRef(null)

  useEffect(() => {
    if (terminalRef.current)
      terminalRef.current.scrollTop = terminalRef.current.scrollHeight
  }, [logs])

  const addLog = useCallback((msg) => {
    setLogs(prev => [...prev, `> ${msg}`])
  }, [])

  // ── Load FFmpeg WASM ────────────────────────────────────────────────
  useEffect(() => {
    const load = async () => {
      try {
        setFfmpegLoading(true)
        setStatus('NAČÍTÁM FFMPEG ENGINE...')
        addLog('Inicializuji FFmpeg WASM engine...')

        ffmpegInstance.on('log', ({ message }) => {
          if (
            message.includes('time=') ||
            message.toLowerCase().includes('error') ||
            message.includes('Duration') ||
            message.includes('Output')
          ) addLog(message.trim())
        })

        const base = window.location.origin
        await ffmpegInstance.load({
          coreURL: await toBlobURL(`${base}/ffmpeg-core.js`, 'text/javascript'),
          wasmURL: await toBlobURL(`${base}/ffmpeg-core.wasm`, 'application/wasm'),
        })

        setFfmpegLoaded(true)
        setFfmpegLoading(false)
        setStatus('PŘIPRAVENO.')
        addLog('FFmpeg engine načten. Systém připraven.')
      } catch (e) {
        const msg = e?.message || String(e) || 'Neznámá chyba'
        setLoadError(msg)
        setFfmpegLoading(false)
        setStatus('CHYBA NAČÍTÁNÍ ENGINU.')
        addLog(`CHYBA: ${msg}`)
        console.error('FFmpeg load error:', e)
      }
    }
    load()
  }, [addLog])

  // ── File selection ──────────────────────────────────────────────────
  const handleFileSelect = useCallback((selectedFile) => {
    if (!selectedFile) return
    const name = selectedFile.name.toLowerCase()
    const isValid =
      selectedFile.type.startsWith('video') ||
      selectedFile.type.startsWith('audio') ||
      name.endsWith('.mp3') ||
      name.endsWith('.mp4')

    if (!isValid) {
      addLog('CHYBA: Pouze MP3 a MP4 soubory jsou podporovány.')
      return
    }

    setFile(selectedFile)
    setOutputFiles([])
    addLog(`Soubor: ${selectedFile.name}`)
    addLog(`Velikost: ${formatSize(selectedFile.size)}`)

    const ext = name.split('.').pop()
    if (selectedFile.size > STREAM_THRESHOLD_BYTES) {
      if (ext === 'mp3') {
        addLog(`ℹ Velký soubor → použiji rychlé streamované dělení (bez WASM).`)
      } else {
        addLog(`⚠ Velký MP4 soubor (${formatSize(selectedFile.size)}).`)
        addLog(`  Zpracování proběhne přes WASM — může selhat při >2 GB.`)
        addLog(`  Pro soubory >2 GB doporučujeme desktop aplikaci.`)
      }
    }
  }, [addLog])

  const handleDrop = useCallback((e) => {
    e.preventDefault()
    setIsDragging(false)
    const dropped = e.dataTransfer.files[0]
    if (dropped) handleFileSelect(dropped)
  }, [handleFileSelect])

  // ── Duration from HTML5 ─────────────────────────────────────────────
  const getMediaDuration = (f) =>
    new Promise((resolve, reject) => {
      const url = URL.createObjectURL(f)
      const isVideo = f.type.startsWith('video') || f.name.toLowerCase().endsWith('.mp4')
      const el = document.createElement(isVideo ? 'video' : 'audio')
      el.preload = 'metadata'
      el.src = url
      el.onloadedmetadata = () => { URL.revokeObjectURL(url); resolve(el.duration) }
      el.onerror = () => { URL.revokeObjectURL(url); reject(new Error('Nelze načíst metadata souboru.')) }
    })

  // ── Streaming split (pure JS, no WASM, any file size) ───────────────
  //    Works well for MP3. For MP4 it produces raw byte-slices which
  //    may not be playable in all players, but the data is intact.
  const splitByteStream = async (f, n, overlapSec, duration) => {
    const ext      = f.name.split('.').pop().toLowerCase()
    const baseName = f.name.slice(0, f.name.lastIndexOf('.'))
    const mimeType = ext === 'mp4' ? 'video/mp4' : 'audio/mpeg'
    const bps      = f.size / duration           // bytes per second (approx)
    const partLen  = duration / n
    const outputs  = []

    for (let i = 0; i < n; i++) {
      const startTime = i * partLen
      const endTime   = i < n - 1 ? Math.min((i + 1) * partLen + overlapSec, duration) : duration
      const startByte = Math.floor(startTime * bps)
      const endByte   = Math.min(Math.ceil(endTime * bps), f.size)

      const outName = `${baseName}_cast_${i + 1}.${ext}`

      setStatus(`ZPRACOVÁVÁM ČÁST ${i + 1} Z ${n}...`)
      setProgress(Math.round((i / n) * 100))
      addLog(`==== ČÁST ${i + 1} ====`)
      addLog(`ČAS: ${startTime.toFixed(2)}S → ${endTime.toFixed(2)}S`)
      addLog(`CÍL: ${outName}`)

      const slice = f.slice(startByte, endByte)
      const url   = URL.createObjectURL(new Blob([slice], { type: mimeType }))
      outputs.push({ name: outName, url, sizeMB: (slice.size / 1024 / 1024).toFixed(2) })
      addLog(`✓ Část ${i + 1} hotova (${(slice.size / 1024 / 1024).toFixed(1)} MB)`)
    }
    return outputs
  }

  // ── WASM split (FFmpeg, best quality, limited by browser RAM) ────────
  const splitWithWasm = async (f, n, overlapSec, duration) => {
    const ext       = f.name.split('.').pop().toLowerCase()
    const baseName  = f.name.slice(0, f.name.lastIndexOf('.'))
    const mimeType  = ext === 'mp4' ? 'video/mp4' : 'audio/mpeg'
    const inputName = `input.${ext}`
    const partLen   = duration / n
    const outputs   = []

    setStatus('NAHRÁVÁM SOUBOR DO PAMĚTI...')
    addLog(`Nahrávám ${formatSize(f.size)} do WASM...`)

    try {
      const buf = await f.arrayBuffer()
      await ffmpegInstance.writeFile(inputName, new Uint8Array(buf))
    } catch (writeErr) {
      const msg = writeErr?.message || String(writeErr)
      if (msg.includes('Code=-1') || msg.includes('could not be read') || msg.includes('memory')) {
        throw new Error(
          `Nedostatek paměti RAM v prohlížeči pro soubor ${formatSize(f.size)}.\n` +
          `Zkuste soubor menší než 300 MB, nebo použijte desktop aplikaci.`
        )
      }
      throw writeErr
    }

    addLog('Soubor nahrán. Spouštím dělení...')

    for (let i = 0; i < n; i++) {
      const startTime = i * partLen
      const endTime   = i < n - 1 ? Math.min((i + 1) * partLen + overlapSec, duration) : duration
      const partDur   = endTime - startTime
      const outName   = `${baseName}_cast_${i + 1}.${ext}`

      setStatus(`ZPRACOVÁVÁM ČÁST ${i + 1} Z ${n}...`)
      setProgress(Math.round((i / n) * 100))
      addLog(`==== ČÁST ${i + 1} ====`)
      addLog(`ČAS: ${startTime.toFixed(2)}S → ${endTime.toFixed(2)}S (${partDur.toFixed(2)}S)`)
      addLog(`CÍL: ${outName}`)

      await ffmpegInstance.exec([
        '-ss', startTime.toFixed(3),
        '-t',  partDur.toFixed(3),
        '-i',  inputName,
        '-c',  'copy',
        outName,
      ])

      const data = await ffmpegInstance.readFile(outName)
      const blob = new Blob([data.buffer], { type: mimeType })
      const url  = URL.createObjectURL(blob)
      outputs.push({ name: outName, url, sizeMB: (blob.size / 1024 / 1024).toFixed(2) })
      addLog(`✓ Část ${i + 1} hotova (${(blob.size / 1024 / 1024).toFixed(1)} MB)`)
      await ffmpegInstance.deleteFile(outName)
    }

    await ffmpegInstance.deleteFile(inputName)
    return outputs
  }

  // ── Main split dispatcher ───────────────────────────────────────────
  const startSplitting = async () => {
    if (!file) { addLog('CHYBA: Nejprve vyberte soubor.'); return }

    const n = parseInt(numParts)
    const o = parseFloat(overlap)
    if (isNaN(n) || n < 2) { addLog('CHYBA: Počet částí musí být alespoň 2.'); return }
    if (isNaN(o) || o < 0) { addLog('CHYBA: Překryv musí být nezáporné číslo.');  return }

    const ext = file.name.split('.').pop().toLowerCase()
    const useStreaming = file.size > STREAM_THRESHOLD_BYTES && ext === 'mp3'
    const needsWasm   = !useStreaming

    if (needsWasm && !ffmpegLoaded) {
      addLog('CHYBA: FFmpeg engine ještě není připraven.')
      return
    }

    try {
      setIsRunning(true)
      setOutputFiles([])
      setLogs(['> SPOUŠTÍM ROZDĚLOVÁNÍ...'])
      setProgress(0)

      setStatus('ZJIŠŤUJI DÉLKU SOUBORU...')
      addLog(`Soubor: ${file.name} (${formatSize(file.size)})`)
      const duration = await getMediaDuration(file)
      addLog(`CELKOVÁ DÉLKA: ${duration.toFixed(2)} S`)

      if (useStreaming) {
        addLog('Režim: STREAMOVANÉ DĚLENÍ (MP3, libovolná velikost)')
      } else {
        addLog('Režim: WASM FFmpeg (bezeztrátový)')
      }

      const outputs = useStreaming
        ? await splitByteStream(file, n, o, duration)
        : await splitWithWasm(file, n, o, duration)

      setOutputFiles(outputs)
      setStatus('HOTOVO!')
      setProgress(100)
      addLog('===============================')
      addLog(`DOKONČENO! ${n} souborů ke stažení.`)

    } catch (e) {
      const raw = e?.message || String(e)
      addLog(`KRITICKÁ CHYBA: ${raw}`)
      setStatus('NASTALA KRITICKÁ CHYBA.')
    } finally {
      setIsRunning(false)
    }
  }

  // ── UI ──────────────────────────────────────────────────────────────
  const fileSizeColor = !file ? null
    : file.size > 2 * 1024 * 1024 * 1024 ? 'var(--c-danger)'
    : file.size > STREAM_THRESHOLD_BYTES  ? '#f59e0b'
    : 'var(--c-success)'

  return (
    <div style={{ maxWidth: '820px', margin: '0 auto', padding: '2rem' }}>

      {/* Masthead */}
      <div className="brutal-header">
        <div className="brutal-accent-line" />
        <div>
          <h1>MARIAN'S SPLITTER</h1>
          <div style={{ marginTop: '0.4rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <span className="badge-accent">v3 WEB</span>
            <span className="badge-accent">WASM</span>
          </div>
        </div>
        <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: '8px' }}>
          {ffmpegLoading && <><span className="spinner" /><span style={{ color: 'var(--c-muted)', fontSize: '0.8rem' }}>Načítám engine...</span></>}
          {ffmpegLoaded  && <span className="engine-ready">● ENGINE READY</span>}
          {loadError     && <span style={{ color: 'var(--c-danger)', fontSize: '0.8rem' }}>● CHYBA ENGINU</span>}
        </div>
      </div>

      {/* Main Card */}
      <div className="brutal-card">
        <div style={{ display: 'flex', alignItems: 'baseline', gap: '0.75rem', marginBottom: '1.5rem' }}>
          <h2>PARAMETRY DĚLENÍ</h2>
          <span style={{ color: 'var(--c-border)', fontSize: '0.75rem' }}>MP3 / MP4 · Bezeztrátový režim</span>
        </div>

        {/* Drop Zone */}
        <div
          className={`drop-zone${isDragging ? ' drag-over' : ''}${file ? ' has-file' : ''}`}
          onDrop={handleDrop}
          onDragOver={(e) => { e.preventDefault(); setIsDragging(true) }}
          onDragLeave={() => setIsDragging(false)}
          onClick={() => fileInputRef.current?.click()}
          role="button" tabIndex={0}
          onKeyDown={(e) => e.key === 'Enter' && fileInputRef.current?.click()}
        >
          <input
            ref={fileInputRef}
            id="fileInput"
            type="file"
            accept=".mp3,.mp4,audio/mpeg,video/mp4"
            style={{ display: 'none' }}
            onChange={(e) => handleFileSelect(e.target.files?.[0])}
          />
          {file ? (
            <div className="drop-zone-content">
              <div className="drop-zone-icon">{file.type.startsWith('video') || file.name.endsWith('.mp4') ? '🎬' : '🎵'}</div>
              <div className="drop-zone-filename">{file.name}</div>
              <div style={{ color: fileSizeColor, fontWeight: 'bold', fontSize: '0.9rem' }}>
                {formatSize(file.size)}
                {file.size > 2 * 1024 * 1024 * 1024 && ' ⚠ VELKÝ'}
              </div>
              <div className="drop-zone-meta">klikni nebo přetáhni pro změnu</div>
            </div>
          ) : (
            <div className="drop-zone-content">
              <div className="drop-zone-icon">📁</div>
              <div className="drop-zone-hint-main">PŘETÁHNI SOUBOR NEBO KLIKNI</div>
              <div className="drop-zone-hint-sub">MP3 nebo MP4 · libovolná velikost</div>
            </div>
          )}
        </div>

        {/* Legend */}
        <div style={{ display: 'flex', gap: '1.5rem', marginBottom: '1rem', fontSize: '0.72rem', color: 'var(--c-muted)' }}>
          <span><span style={{ color: 'var(--c-success)' }}>●</span> &lt;300 MB — WASM (přesné)</span>
          <span><span style={{ color: '#f59e0b' }}>●</span> 300 MB–2 GB — WASM (může selhat)</span>
          <span><span style={{ color: 'var(--c-danger)' }}>●</span> &gt;2 GB — použijte desktop app</span>
          <span style={{ marginLeft: 'auto' }}><span style={{ color: 'var(--c-accent)' }}>★</span> MP3 streamuje vždy</span>
        </div>

        {/* Settings */}
        <div style={{ display: 'flex', gap: '1.5rem', marginBottom: '1.5rem' }}>
          <div style={{ flex: 1 }}>
            <label className="brutal-label" htmlFor="numParts">POČET ČÁSTÍ</label>
            <input id="numParts" type="number" className="brutal-input" value={numParts}
              onChange={e => setNumParts(e.target.value)} disabled={isRunning} min="2" />
          </div>
          <div style={{ flex: 1 }}>
            <label className="brutal-label" htmlFor="overlap">PŘEKRYV (S)</label>
            <input id="overlap" type="number" step="0.5" className="brutal-input" value={overlap}
              onChange={e => setOverlap(e.target.value)} disabled={isRunning} min="0" />
          </div>
        </div>

        <button
          id="startBtn"
          className={isRunning ? 'brutal-btn-danger' : 'brutal-btn-primary'}
          onClick={startSplitting}
          disabled={isRunning || (!ffmpegLoaded && file && file.size <= STREAM_THRESHOLD_BYTES)}
        >
          {isRunning ? '⏳ ZPRACOVÁVÁM...' : !ffmpegLoaded && !loadError ? '⌛ NAČÍTÁM ENGINE...' : '▶ ROZDĚLIT SOUBOR'}
        </button>
      </div>

      {/* Downloads */}
      {outputFiles.length > 0 && (
        <div className="brutal-card">
          <h2 style={{ marginBottom: '1rem' }}>⬇ VÝSLEDKY KE STAŽENÍ</h2>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
            {outputFiles.map((f, i) => (
              <a key={i} href={f.url} download={f.name} id={`download-${i + 1}`} className="download-item">
                <span className="download-part">ČÁST {i + 1}</span>
                <span className="download-name">{f.name}</span>
                <span className="download-size">{f.sizeMB} MB ↓</span>
              </a>
            ))}
          </div>
          <p style={{ color: 'var(--c-muted)', fontSize: '0.75rem', marginTop: '1rem' }}>
            ⚠ Stáhni soubory před zavřením stránky — po obnovení budou smazány.
          </p>
        </div>
      )}

      {/* Terminal */}
      <div className="brutal-card" style={{ marginBottom: 0 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.75rem', alignItems: 'center' }}>
          <h2 style={{ fontSize: '0.9rem', letterSpacing: '0.1em' }}>TERMINÁL / STAV</h2>
          <span style={{ color: 'var(--c-accent)', fontWeight: 'bold', fontSize: '0.85rem' }}>{status}</span>
        </div>
        <div className="brutal-progress-bar">
          <div className="brutal-progress-fill" style={{ width: `${progress}%` }} />
        </div>
        <div className="brutal-terminal" ref={terminalRef}>
          {logs.map((line, i) => (
            <div key={i} className={
              `log-line${line.includes('CHYBA') ? ' log-error' : ''}${line.includes('✓') || line.includes('DOKONČENO') ? ' log-success' : ''}${line.includes('⚠') ? ' log-warn' : ''}`
            }>{line}</div>
          ))}
        </div>
      </div>
    </div>
  )
}

export default App
