import { useState } from 'react'
import { Server, Cpu, Database, RefreshCw, CheckCircle2, AlertTriangle, XCircle, HardDrive } from 'lucide-react'

function SystemHealthMonitor({ status, onRefresh }) {
  const [refreshing, setRefreshing] = useState(false)

  const handleRefresh = async () => {
    setRefreshing(true)
    if (onRefresh) await onRefresh()
    setTimeout(() => setRefreshing(false), 800)
  }

  const services = [
    {
      name: 'FastAPI Backend',
      port: '8000',
      online: status?.healthy,
      details: status?.healthy ? 'HTTP REST API Online' : 'Connection Refused',
      icon: Server,
    },
    {
      name: 'Primary LLM Engine (LM Studio)',
      port: '1234',
      online: status?.ollamaAvailable,
      details: status?.activeModel || 'oreal-deepseek-r1-distill-qwen-7b',
      icon: Cpu,
    },
    {
      name: 'Prompt Refiner (Ollama)',
      port: '11434',
      online: status?.refinerAvailable || status?.ollamaAvailable,
      details: status?.refinerModel || 'qwen3:4b-thinking',
      icon: Cpu,
    },
    {
      name: 'Continuous Memory Agent',
      port: '8001',
      online: !status?.error,
      details: 'SQLite feedback & ChromaDB loop',
      icon: Database,
    },
  ]

  return (
    <div className="system-health-monitor-view">
      <div className="monitor-header-banner">
        <div className="title-group">
          <Server size={22} color="var(--accent-primary)" />
          <div>
            <h3>Platform Telemetry &amp; System Health Cockpit</h3>
            <p>Real-time microservice status, local model runtimes &amp; communication sockets</p>
          </div>
        </div>

        <button
          type="button"
          className="btn-refresh-telemetry"
          onClick={handleRefresh}
          disabled={refreshing}
        >
          <RefreshCw size={14} className={refreshing ? 'spinner-rotate' : ''} />
          <span>Refresh Sockets</span>
        </button>
      </div>

      <div className="services-health-grid">
        {services.map((svc, i) => {
          const Icon = svc.icon
          return (
            <div key={i} className={`service-health-card ${svc.online ? 'online' : 'offline'}`}>
              <div className="card-top">
                <div className="service-icon-box">
                  <Icon size={18} />
                </div>
                <div className="status-indicator-tag">
                  {svc.online ? (
                    <>
                      <CheckCircle2 size={13} color="var(--accent-success)" />
                      <span className="online-text">Port {svc.port} Active</span>
                    </>
                  ) : (
                    <>
                      <AlertTriangle size={13} color="var(--accent-error)" />
                      <span className="offline-text">Port {svc.port} Inactive</span>
                    </>
                  )}
                </div>
              </div>

              <h4 className="service-name">{svc.name}</h4>
              <p className="service-details">{svc.details}</p>
            </div>
          )
        })}
      </div>

      <div className="runtime-info-card">
        <div className="info-header">
          <HardDrive size={16} color="var(--accent-secondary)" />
          <h4>Operational Configuration</h4>
        </div>
        <div className="info-table-grid">
          <div className="info-cell">
            <span className="info-k">Frontend Framework:</span>
            <span className="info-v highlight-cyan">React 18.2 + Vite 5 (Exclusive)</span>
          </div>
          <div className="info-cell">
            <span className="info-k">3D WebGL Engine:</span>
            <span className="info-v">React Three Fiber 8.18 + Drei + Three.js</span>
          </div>
          <div className="info-cell">
            <span className="info-k">State Management:</span>
            <span className="info-v">Zustand Distributed Store Architecture</span>
          </div>
          <div className="info-cell">
            <span className="info-k">Streaming Protocol:</span>
            <span className="info-v">Server-Sent Events (SSE / text/event-stream)</span>
          </div>
        </div>
      </div>
    </div>
  )
}

export default SystemHealthMonitor

