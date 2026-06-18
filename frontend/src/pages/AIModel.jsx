import { useState } from 'react'
import AISignals from './AISignals'
import ModelCenter from './ModelCenter'

export default function AIModel() {
  const [view, setView] = useState('signals')

  return (
    <div>
      <h2 className="page-title">AI模型</h2>
      <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
        <button
          className="btn"
          style={{ background: view === 'signals' ? 'var(--green2)' : 'var(--bg3)', color: view === 'signals' ? '#000' : 'var(--text)' }}
          onClick={() => setView('signals')}
        >
          AI信号
        </button>
        <button
          className="btn"
          style={{ background: view === 'model' ? 'var(--green2)' : 'var(--bg3)', color: view === 'model' ? '#000' : 'var(--text)' }}
          onClick={() => setView('model')}
        >
          模型管理
        </button>
      </div>
      <div>
        {view === 'signals' && <AISignals />}
        {view === 'model' && <ModelCenter />}
      </div>
    </div>
  )
}
