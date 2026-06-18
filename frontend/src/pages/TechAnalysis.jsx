import { useState } from 'react'
import ChanLunPage from './ChanLunPage'
import IndicatorsPage from './IndicatorsPage'

export default function TechAnalysis() {
  const [view, setView] = useState('chanlun')

  return (
    <div>
      <h2 className="page-title">技术分析</h2>
      <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
        <button
          className="btn"
          style={{ background: view === 'chanlun' ? 'var(--green2)' : 'var(--bg3)', color: view === 'chanlun' ? '#000' : 'var(--text)' }}
          onClick={() => setView('chanlun')}
        >
          缠论分析
        </button>
        <button
          className="btn"
          style={{ background: view === 'indicators' ? 'var(--green2)' : 'var(--bg3)', color: view === 'indicators' ? '#000' : 'var(--text)' }}
          onClick={() => setView('indicators')}
        >
          技术指标
        </button>
      </div>
      <div>
        {view === 'chanlun' && <ChanLunPage />}
        {view === 'indicators' && <IndicatorsPage />}
      </div>
    </div>
  )
}
