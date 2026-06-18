import { useState } from 'react'
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts'

const STRATEGIES = [
  { key: 'breakout', name: '放量突破' },
  { key: 'bluechip', name: '低估值蓝筹' },
  { key: 'limitup', name: '涨停板' },
  { key: 'active', name: '高换手活跃' },
]

export default function BacktestPage() {
  const [strategy, setStrategy] = useState('breakout')
  const [days, setDays] = useState(252)
  const [results, setResults] = useState(null)
  const [loading, setLoading] = useState(false)

  const run = async () => {
    setLoading(true)
    try {
      const res = await fetch(`/api/backtest/run?strategy=${strategy}&days=${days}`)
      const d = await res.json()
      if (d.code === 0) setResults(d)
    } catch (e) { console.error(e) }
    finally { setLoading(false) }
  }

  return (
    <div>
      <h2 className="page-title">回测分析</h2>

      <div className="card-grid" style={{ marginBottom: 16 }}>
        {STRATEGIES.map(s => (
          <div key={s.key}
            className="stat-card"
            style={{ cursor: 'pointer', textAlign: 'center', border: strategy === s.key ? '1px solid var(--blue)' : '1px solid transparent' }}
            onClick={() => setStrategy(s.key)}
          >
            <div style={{ fontWeight: 'bold', marginBottom: 4 }}>{s.name}</div>
          </div>
        ))}
      </div>

      <div style={{ display: 'flex', gap: 12, marginBottom: 16, alignItems: 'center' }}>
        <select value={days} onChange={e => setDays(Number(e.target.value))}
          style={{ background: 'var(--bg3)', border: '1px solid var(--border)', color: 'var(--text)', padding: '6px 12px', borderRadius: 6 }}>
          <option value={126}>半年</option>
          <option value={252}>1年</option>
          <option value={504}>2年</option>
          <option value={756}>3年</option>
        </select>
        <button className="btn btn-primary" onClick={run} disabled={loading}>
          {loading ? '回测中...' : '运行回测'}
        </button>
      </div>

      {!results ? (
        <div className="card" style={{ textAlign: 'center', padding: 60 }}>
          <p style={{ color: 'var(--text2)' }}>选择策略和周期，点击「运行回测」</p>
        </div>
      ) : (
        <>
          <div className="card-grid" style={{ marginBottom: 16 }}>
            <StatCard label="策略" value={results.strategy} />
            <StatCard label="累计收益" value={`${results.metrics.total_return_pct}%`} color={results.metrics.total_return_pct > 0 ? 'up' : 'down'} />
            <StatCard label="年化收益" value={`${results.metrics.annual_return_pct}%`} color={results.metrics.annual_return_pct > 0 ? 'up' : 'down'} />
            <StatCard label="Sharpe" value={results.metrics.sharpe_ratio} />
            <StatCard label="最大回撤" value={`${results.metrics.max_drawdown_pct}%`} color="down" />
            <StatCard label="胜率" value={`${results.metrics.win_rate_pct}%`} />
            <StatCard label="Calmar" value={results.metrics.calmar_ratio} />
            <StatCard label="Sortino" value={results.metrics.sortino_ratio} />
            <StatCard label="年化波动" value={`${results.metrics.annual_volatility_pct}%`} />
            <StatCard label="回测天数" value={results.metrics.total_days} />
          </div>

          <div className="card">
            <div className="card-title">净值曲线 — {results.strategy} 策略</div>
            <ResponsiveContainer width="100%" height={350}>
              <AreaChart data={results.equity}>
                <defs>
                  <linearGradient id="colorValue" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#3b82f6" stopOpacity={0.3} />
                    <stop offset="100%" stopColor="#3b82f6" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                <XAxis dataKey="date" tick={{ fill: '#6b7280', fontSize: 10 }} tickFormatter={d => d.slice(5)} />
                <YAxis tick={{ fill: '#6b7280', fontSize: 10 }} tickFormatter={v => `${(v / 10000).toFixed(0)}万`} />
                <Tooltip contentStyle={{ background: '#1f2937', border: '1px solid #374151', borderRadius: 8 }} labelStyle={{ color: '#9ca3af' }} />
                <Area type="monotone" dataKey="value" stroke="#3b82f6" fill="url(#colorValue)" strokeWidth={2} />
              </AreaChart>
            </ResponsiveContainer>
          </div>

          <div className="card">
            <div className="card-title">回撤曲线</div>
            <ResponsiveContainer width="100%" height={200}>
              <AreaChart data={results.drawdown}>
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                <XAxis dataKey="date" tick={{ fill: '#6b7280', fontSize: 10 }} tickFormatter={d => d.slice(5)} />
                <YAxis tick={{ fill: '#6b7280', fontSize: 10 }} tickFormatter={v => `${v}%`} domain={['auto', 0]} />
                <Tooltip contentStyle={{ background: '#1f2937', border: '1px solid #374151', borderRadius: 8 }} />
                <Area type="monotone" dataKey="dd" stroke="#ef4444" fill="#ef444433" strokeWidth={1} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </>
      )}
    </div>
  )
}

function StatCard({ label, value, color = '' }) {
  return (
    <div className="stat-card">
      <div className="stat-label">{label}</div>
      <div className={`stat-value ${color}`} style={{ fontSize: 16 }}>{value}</div>
    </div>
  )
}
