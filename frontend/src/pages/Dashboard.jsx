import { useState, useEffect, useCallback } from 'react'
import { fmt } from '../hooks/useApi'
import {
  AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid,
  ReferenceLine, BarChart, Bar, Cell, PieChart, Pie, Legend,
} from 'recharts'

export default function Dashboard({ onSelect }) {
  const [overview, setOverview] = useState([])
  const [dashData, setDashData] = useState(null)
  const [curveData, setCurveData] = useState(null)
  const [quotes, setQuotes] = useState([])
  const [risk, setRisk] = useState(null)
  const [autotrade, setAutotrade] = useState(null)
  const [logs, setLogs] = useState([])
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const [ov, dq, eq, qt, rk, at, lg] = await Promise.all([
        fetch('/api/market/overview').then(r => r.json()),
        fetch('/api/dashboard/overview').then(r => r.json()),
        fetch('/api/dashboard/equity-curve').then(r => r.json()),
        fetch('/api/market/quotes?page=1&page_size=10&sort_by=amount').then(r => r.json()),
        fetch('/api/risk/status').then(r => r.json()).catch(() => ({ data: {} })),
        fetch('/api/autotrade/status').then(r => r.json()).catch(() => ({ data: {} })),
        fetch('/api/logs?level=ALERT&page_size=5').then(r => r.json()).catch(() => ({ data: [] })),
      ])
      setOverview(ov.data || [])
      setDashData(dq.data || {})
      setCurveData(eq.data || {})
      setQuotes(qt.data || [])
      setRisk(rk.data || {})
      setAutotrade(at.data || {})
      setLogs(lg.data || [])
    } catch (e) { console.error(e) }
    finally { setLoading(false) }
  }, [])

  useEffect(() => { load() }, [load])
  useEffect(() => { const t = setInterval(load, 30000); return () => clearInterval(t) }, [load])

  if (loading) return <div className="loading">加载数据大屏...</div>

  const d = dashData || {}
  const eq = curveData?.equity || []
  const dd = curveData?.drawdown || []
  const stratNames = d.strategies_used || []

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <h2 className="page-title" style={{ margin: 0 }}>量化交易系统 v4.0</h2>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          <span style={{ fontSize: 12, color: 'var(--text3)' }}>
            {d.sh_index ? `上证 ${d.sh_index?.toFixed(2)} ${d.sh_change_pct >= 0 ? '+' : ''}${d.sh_change_pct?.toFixed(2)}%` : ''}
          </span>
          <button className="btn btn-sm" onClick={load}>刷新</button>
        </div>
      </div>

      {/* 第一行：核心指标 */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(6, 1fr)', gap: 12, marginBottom: 20 }}>
        <BigCard label="总资产" value={`${(d.equity / 10000).toFixed(2)}万`}
          sub={`现金 ${(d.cash / 10000).toFixed(2)}万`} />
        <BigCard label="累计收益" value={`${d.total_return_pct >= 0 ? '+' : ''}${d.total_return_pct}%`}
          color={d.total_return_pct >= 0 ? 'var(--red)' : 'var(--green)'}
          sub={`交易${d.total_trades || 0}笔`} />
        <BigCard label="胜率" value={`${d.win_rate || 0}%`}
          color={(d.win_rate || 0) >= 50 ? 'var(--green2)' : 'var(--text)'}
          sub={`赢${d.sell_trades || 0}笔卖出`} />
        <BigCard label="盈亏比" value={d.profit_loss_ratio || '-'}
          color={(d.profit_loss_ratio || 0) >= 1 ? 'var(--green2)' : 'var(--text)'} />
        <BigCard label="自动交易" value={autotrade?.enabled ? '运行中' : '已停止'}
          color={autotrade?.enabled ? 'var(--green2)' : 'var(--text3)'}
          sub={autotrade?.strategy || ''} />
        <BigCard label="风控" value={risk?.paused ? '暂停' : '正常'}
          color={risk?.paused ? 'var(--red)' : 'var(--green2)'}
          sub={risk?.position_limit_pct ? `仓位${risk?.total_position_pct || 0}%` : ''} />
      </div>

      {/* 第二行：净值曲线 + 回撤曲线 */}
      <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 16, marginBottom: 20 }}>
        <div className="card">
          <div className="card-title">净值曲线</div>
          {eq.length > 0 ? (
            <ResponsiveContainer width="100%" height={280}>
              <AreaChart data={eq}>
                <defs>
                  <linearGradient id="eqG" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#00e676" stopOpacity={0.3} />
                    <stop offset="100%" stopColor="#00e676" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#21262d" />
                <XAxis dataKey="date" tick={{ fill: '#6e7681', fontSize: 10 }} tickFormatter={d => d?.slice(5) || ''} />
                <YAxis tick={{ fill: '#6e7681', fontSize: 10 }} tickFormatter={v => `${(v / 10000).toFixed(0)}万`} />
                <Tooltip contentStyle={{ background: '#161b22', border: '1px solid #30363d', borderRadius: 8, color: '#e6edf3' }}
                  formatter={v => fmt(v)} />
                <ReferenceLine y={1000000} stroke="#6e7681" strokeDasharray="5 5" />
                <Area type="monotone" dataKey="value" stroke="#00e676" fill="url(#eqG)" strokeWidth={2} />
              </AreaChart>
            </ResponsiveContainer>
          ) : (
            <div style={{ height: 280, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#6e7681' }}>
              暂无净值数据
            </div>
          )}
        </div>

        <div className="card">
          <div className="card-title">回撤曲线</div>
          {dd.length > 0 ? (
            <ResponsiveContainer width="100%" height={280}>
              <AreaChart data={dd}>
                <CartesianGrid strokeDasharray="3 3" stroke="#21262d" />
                <XAxis dataKey="date" tick={{ fill: '#6e7681', fontSize: 10 }} tickFormatter={d => d?.slice(5) || ''} />
                <YAxis tick={{ fill: '#6e7681', fontSize: 10 }} tickFormatter={v => `${v}%`} domain={['auto', 0]} />
                <Tooltip contentStyle={{ background: '#161b22', border: '1px solid #30363d', borderRadius: 8, color: '#e6edf3' }}
                  formatter={v => `${v}%`} />
                <ReferenceLine y={-3} stroke="#f59e0b" strokeDasharray="5 5" />
                <Area type="monotone" dataKey="dd" stroke="#ff1744" fill="#ff174422" strokeWidth={1.5} />
              </AreaChart>
            </ResponsiveContainer>
          ) : (
            <div style={{ height: 280, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#6e7681' }}>
              暂无回撤数据
            </div>
          )}
        </div>
      </div>

      {/* 第三行：大盘 + 热门 + 告警 */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 16 }}>
        {/* 大盘 */}
        <div className="card">
          <div className="card-title">大盘指数</div>
          {overview.map(idx => (
            <div key={idx.code} style={{
              display: 'flex', justifyContent: 'space-between', padding: '8px 12px',
              background: 'var(--bg)', borderRadius: 6, marginBottom: 6,
            }}>
              <span>{idx.name}</span>
              <span className={idx.change_pct >= 0 ? 'up' : 'down'} style={{ fontWeight: 'bold' }}>
                {idx.price?.toFixed(2)} ({idx.change_pct >= 0 ? '+' : ''}{idx.change_pct?.toFixed(2)}%)
              </span>
            </div>
          ))}
        </div>

        {/* 热门股票 */}
        <div className="card">
          <div className="card-title">热门 TOP5</div>
          <table>
            <thead><tr><th>名称</th><th>价格</th><th>涨跌</th><th>成交额</th></tr></thead>
            <tbody>
              {quotes.slice(0, 5).map(r => (
                <tr key={r.code}>
                  <td><span className="link" onClick={() => onSelect(r.code)}>{r.name}</span></td>
                  <td className={(r.pct_chg || 0) >= 0 ? 'up' : 'down'}>{r.price?.toFixed(2)}</td>
                  <td className={(r.pct_chg || 0) >= 0 ? 'up' : 'down'}>
                    {(r.pct_chg || 0) >= 0 ? '+' : ''}{(r.pct_chg || 0)?.toFixed(2)}%
                  </td>
                  <td>{fmt(r.amount)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* 实时告警 */}
        <div className="card">
          <div className="card-title">实时告警</div>
          {logs.length === 0 ? (
            <p style={{ color: 'var(--text3)', padding: 20, textAlign: 'center' }}>无告警</p>
          ) : (
            <div style={{ maxHeight: 280, overflow: 'auto' }}>
              {logs.map((l, i) => (
                <div key={i} style={{
                  padding: 6, marginBottom: 4, borderRadius: 4, fontSize: 12,
                  background: l.level === 'ALERT' || l.level === 'ERROR' ? 'rgba(239,68,68,0.08)' : 'rgba(234,179,8,0.08)',
                  borderLeft: `3px solid ${l.level === 'ALERT' || l.level === 'ERROR' ? 'var(--red)' : 'var(--yellow)'}`,
                }}>
                  <div style={{ color: 'var(--text3)', fontSize: 11 }}>{l.time}</div>
                  <div>{l.msg}</div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function BigCard({ label, value, sub, color }) {
  return (
    <div style={{
      background: 'var(--bg2)', border: '1px solid var(--border)', borderRadius: 10,
      padding: '16px 12px', textAlign: 'center',
    }}>
      <div style={{ fontSize: 12, color: 'var(--text3)', marginBottom: 8 }}>{label}</div>
      <div style={{ fontSize: 22, fontWeight: 'bold', color: color || 'var(--text)' }}>{value}</div>
      {sub && <div style={{ fontSize: 11, color: 'var(--text3)', marginTop: 4 }}>{sub}</div>}
    </div>
  )
}
