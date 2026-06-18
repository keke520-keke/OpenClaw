import { useState } from 'react'
import MarketOverview from '../components/MarketOverview'
import QuoteTable from '../components/QuoteTable'
import StockDetail from '../components/StockDetail'

export default function Market({ selected, onSelect }) {
  const [view, setView] = useState('quotes')

  if (selected) {
    return (
      <div>
        <StockDetail code={selected} onBack={() => onSelect(null)} />
      </div>
    )
  }

  return (
    <div>
      <h2 className="page-title">实时行情</h2>
      <div className="tab-bar">
        <button className={`tab-btn ${view === 'quotes' ? 'active' : ''}`} onClick={() => setView('quotes')}>行情列表</button>
        <button className={`tab-btn ${view === 'overview' ? 'active' : ''}`} onClick={() => setView('overview')}>大盘概览</button>
      </div>
      {view === 'quotes' && <QuoteTable onSelect={onSelect} />}
      {view === 'overview' && <MarketOverview />}
    </div>
  )
}
