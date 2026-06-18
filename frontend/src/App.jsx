import { useState } from 'react'
import Dashboard from './pages/Dashboard'
import Market from './pages/Market'
import Screener from './pages/Screener'
import BacktestPage from './pages/BacktestPage'
import FactorsPage from './pages/FactorsPage'
import AutoTrade from './pages/AutoTrade'
import TechAnalysis from './pages/TechAnalysis'
import AIModel from './pages/AIModel'
import RiskMonitor from './pages/RiskMonitor'
import PortfolioPage from './pages/PortfolioPage'
import LogPage from './pages/LogPage'
import WatchlistPage from './pages/WatchlistPage'
import './App.css'

const TABS = [
  { key: 'dashboard', label: '仪表盘', icon: 'D' },
  { key: 'market', label: '行情总览', icon: 'M' },
  { key: 'watch', label: '自选', icon: 'W' },
  { key: 'screener', label: '选股打分', icon: 'S' },
  { key: 'tech', label: '技术分析', icon: 'T' },
  { key: 'auto', label: '自动交易', icon: 'A' },
  { key: 'backtest', label: '回测复盘', icon: 'B' },
  { key: 'ai', label: 'AI模型', icon: 'AI' },
  { key: 'portfolio', label: '组合管理', icon: 'P' },
  { key: 'risk', label: '风控监控', icon: 'RK' },
  { key: 'factors', label: '因子', icon: 'F' },
  { key: 'logs', label: '日志', icon: 'LG' },
]

export default function App() {
  const [tab, setTab] = useState('dashboard')
  const [selectedStock, setSelectedStock] = useState(null)

  return (
    <div className="app">
      <aside className="sidebar">
        <div className="logo">
          <span className="logo-icon">&#9670;</span>
          量化交易系统
        </div>
        <div className="version">v4.0</div>
        <nav>
          {TABS.map((t) => (
            <button
              key={t.key}
              className={`nav-item ${tab === t.key ? 'active' : ''}`}
              onClick={() => { setTab(t.key); setSelectedStock(null); }}
            >
              <span className="nav-icon">{t.icon}</span>
              {t.label}
            </button>
          ))}
        </nav>
      </aside>

      <main className="main-content">
        {tab === 'dashboard' && <Dashboard onSelect={setSelectedStock} />}
        {tab === 'market' && <Market selected={selectedStock} onSelect={setSelectedStock} />}
        {tab === 'watch' && <WatchlistPage onSelect={setSelectedStock} />}
        {tab === 'screener' && <Screener onSelect={setSelectedStock} />}
        {tab === 'tech' && <TechAnalysis onSelect={setSelectedStock} />}
        {tab === 'auto' && <AutoTrade />}
        {tab === 'backtest' && <BacktestPage />}
        {tab === 'ai' && <AIModel />}
        {tab === 'portfolio' && <PortfolioPage />}
        {tab === 'risk' && <RiskMonitor />}
        {tab === 'factors' && <FactorsPage />}
        {tab === 'logs' && <LogPage />}
      </main>
    </div>
  )
}
