import { useState } from 'react'
import RiskSettings from './RiskSettings'
import Monitor from './Monitor'

export default function RiskMonitor() {
  const [view, setView] = useState('risk')

  return (
    <div>
      <h2 className="page-title">风控监控</h2>
      <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
        <button
          className="btn"
          style={{ background: view === 'risk' ? 'var(--green2)' : 'var(--bg3)', color: view === 'risk' ? '#000' : 'var(--text)' }}
          onClick={() => setView('risk')}
        >
          风控设置
        </button>
        <button
          className="btn"
          style={{ background: view === 'monitor' ? 'var(--green2)' : 'var(--bg3)', color: view === 'monitor' ? '#000' : 'var(--text)' }}
          onClick={() => setView('monitor')}
        >
          市场监控
        </button>
      </div>
      <div>
        {view === 'risk' && <RiskSettings />}
        {view === 'monitor' && <Monitor />}
      </div>
    </div>
  )
}
