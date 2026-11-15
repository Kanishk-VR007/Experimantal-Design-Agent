import { useState, useRef } from 'react'
import { UploadCloud, FileSpreadsheet, CheckCircle2, AlertCircle, Trash2 } from 'lucide-react'

function DatasetUploader({ onDatasetLoaded, disabled }) {
  const [fileInfo, setFileInfo] = useState(null)
  const [previewRows, setPreviewRows] = useState([])
  const [error, setError] = useState(null)
  const fileInputRef = useRef(null)

  const handleFileChange = (e) => {
    const file = e.target.files?.[0]
    if (!file) return

    if (!file.name.endsWith('.csv') && !file.name.endsWith('.txt')) {
      setError('Please upload a valid .csv tabular file')
      return
    }

    setError(null)
    const reader = new FileReader()
    reader.onload = (event) => {
      try {
        const text = event.target?.result
        const lines = text.split('\n').filter((l) => l.trim().length > 0)
        if (lines.length > 0) {
          const headers = lines[0].split(',').map((h) => h.trim())
          const rows = lines.slice(1, 6).map((line) => line.split(',').map((c) => c.trim()))
          setFileInfo({
            name: file.name,
            size: `${(file.size / 1024).toFixed(1)} KB`,
            rowCount: lines.length - 1,
            colCount: headers.length,
            headers
          })
          setPreviewRows(rows)
          if (onDatasetLoaded) {
            onDatasetLoaded({ name: file.name, headers, rowCount: lines.length - 1, raw: text })
          }
        }
      } catch (err) {
        setError('Error parsing tabular dataset: ' + err.message)
      }
    }
    reader.readAsText(file)
  }

  const handleClear = () => {
    setFileInfo(null)
    setPreviewRows([])
    setError(null)
    if (fileInputRef.current) fileInputRef.current.value = ''
    if (onDatasetLoaded) onDatasetLoaded(null)
  }

  return (
    <div className="dataset-uploader">
      <input
        type="file"
        ref={fileInputRef}
        onChange={handleFileChange}
        accept=".csv,.txt"
        style={{ display: 'none' }}
        disabled={disabled}
      />

      {!fileInfo ? (
        <div
          className="uploader-dropzone"
          onClick={() => !disabled && fileInputRef.current?.click()}
        >
          <UploadCloud size={24} className="upload-icon" />
          <div className="upload-text">
            <span className="upload-title">Drop CSV reference dataset (Optional)</span>
            <span className="upload-sub">Supports baseline empirical data for simulation comparison</span>
          </div>
        </div>
      ) : (
        <div className="uploader-file-card">
          <div className="file-card-header">
            <div className="file-card-info">
              <FileSpreadsheet size={18} color="var(--accent-primary)" />
              <span className="file-name">{fileInfo.name}</span>
              <span className="file-badge">{fileInfo.rowCount} rows · {fileInfo.colCount} cols</span>
            </div>
            <button type="button" className="btn-icon-clear" onClick={handleClear} title="Remove file">
              <Trash2 size={14} />
            </button>
          </div>

          {previewRows.length > 0 && (
            <div className="table-preview-scroll">
              <table className="mini-preview-table">
                <thead>
                  <tr>
                    {fileInfo.headers.map((h, i) => (
                      <th key={i}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {previewRows.map((row, ri) => (
                    <tr key={ri}>
                      {row.map((col, ci) => (
                        <td key={ci}>{col}</td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {error && (
        <div className="upload-error">
          <AlertCircle size={14} />
          <span>{error}</span>
        </div>
      )}
    </div>
  )
}

export default DatasetUploader

