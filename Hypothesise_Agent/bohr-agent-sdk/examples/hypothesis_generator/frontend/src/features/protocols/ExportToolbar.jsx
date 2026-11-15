import { useState } from 'react'
import { Copy, Check, Download, FileJson, Share2 } from 'lucide-react'

function ExportToolbar({ designText, topic, papers = [] }) {
  const [copied, setCopied] = useState(false)

  const handleCopy = () => {
    if (!designText) return
    navigator.clipboard.writeText(designText)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const handleDownloadMarkdown = () => {
    if (!designText) return
    const blob = new Blob([designText], { type: 'text/markdown;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `experimental_protocol_${Date.now()}.md`
    a.click()
    URL.revokeObjectURL(url)
  }

  const handleDownloadJSON = () => {
    const payload = {
      title: 'Experimental Research Protocol',
      topic,
      generatedAt: new Date().toISOString(),
      protocolMarkdown: designText,
      groundedLiterature: papers,
    }
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `experimental_protocol_${Date.now()}.json`
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="export-toolbar">
      <button
        type="button"
        className="btn-toolbar"
        onClick={handleCopy}
        title="Copy protocol to clipboard"
        disabled={!designText}
      >
        {copied ? <Check size={14} color="#10b981" /> : <Copy size={14} />}
        <span>{copied ? 'Copied' : 'Copy'}</span>
      </button>

      <button
        type="button"
        className="btn-toolbar"
        onClick={handleDownloadMarkdown}
        title="Download Markdown file"
        disabled={!designText}
      >
        <Download size={14} />
        <span>Download .md</span>
      </button>

      <button
        type="button"
        className="btn-toolbar"
        onClick={handleDownloadJSON}
        title="Export full JSON protocol & literature payload"
        disabled={!designText}
      >
        <FileJson size={14} />
        <span>Export JSON</span>
      </button>
    </div>
  )
}

export default ExportToolbar

