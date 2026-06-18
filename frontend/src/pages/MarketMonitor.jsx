import { useState, useEffect, useCallback } from 'react'
import { fmt } from '../hooks/useApi'
import {
  AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid,
  BarChart, Bar, Cell, ReferenceLine
} from 'recharts'

export default function MarketMonitor({ onSelect }) {
  const [indexData, setIndexData] = useState({ spot: [], kline: {} })
  const [industryData, setIndustryData] = useState(null)
  const [watchlist, setWatchlist] = useState([])
  const [watchInput, setWatchInput] = useState('600519,000858,300750')
  const [loading, setLoading] = useState(true)
  const [activeIndex, setActiveIndex] = useState('sh000001')

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const [idx, ind] = await Promise.all([
        fetch('/api/market/indices').then(r => r.json()),
        fetch('/api/market/industry-flow').then(r => r.json()),
      ])
      setIndexData(idx)
      setIndustryData(ind.data)
      // Load watchlist prices
      const codes = watchInput.split(',').filter(Boolean)
      if (codes.length) {
        const resp = await fetch(`/api/stock/list`)
        const all = await resp.json()
        if (all.code === 0) {
          setWatchlist(all.data.filter(s => codes.includes(s.code)))
        }
      }
    } catch (e) { console.error(e) }
    finally { setLoading(false) }
  }, [watchInput])

  useEffect(() => { load() }, [load])
  useEffect(() => { const t = setInterval(load, 30000); return () => clearInterval(t) }, [load])

  const spot = indexData.spot || []
  const kline = indexData.kline?.[activeIndex] || []
  const sectors = industryData?.sectors || []
  const summary = industryData?.summary || {}

  // Heatmap colors
  const getColor = (pct) => {
    if (pct > 3) return '#dc2626'
    if (pct > 1) return '#ef4444'
    if (pct > 0) return '#f87171'
    if (pct === 0) return '#6b7280'
    if (pct > -1) return '#4ade80'
    if (pct > -3) return '#22c55e'
    return '#15803d'
  }

  if (loading) return <div className="loading">加载市场监控...</div>

  return (
    <div>
      <h2 className="page-title">市场监控</h2>

      {/* 大盘指数 */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12, marginBottom: 20 }}>
        {spot.map(idx => (
          <div key={idx.code}
            className="stat-card"
            style={{ cursor: 'pointer', border: activeIndex === idx.code ? '1px solid var(--blue)' : '1px solid transparent' }}
            onClick={() => setActiveIndex(idx.code)}>
            <div style={{ fontSize: 12, color: 'var(--text3)', marginBottom: 4 }}>{idx.name}</div>
            <div style={{ fontSize: 24, fontWeight: 'bold', color: idx.change_pct >= 0 ? 'var(--red)' : 'var(--green)' }}>
              {idx.price?.toFixed(2)}
            </div>
            <div style={{ fontSize: 13, color: idx.change_pct >= 0 ? 'var(--red)' : 'var(--green)', marginTop: 2 }}>
              {idx.change_pct >= 0 ? '+' : ''}{idx.change_pct?.toFixed(2)}%
              ({idx.change_amt >= 0 ? '+' : ''}{idx.change_amt?.toFixed(2)})
            </div>
            <div style={{ fontSize: 11, color: 'var(--text3)', marginTop: 4 }}>
              {idx.name2} | 振幅 {idx.amplitude?.toFixed(2)}%
            </div>
          </div>
        ))}
      </div>

      {/* K线图 + 行业热力图 */}
      <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 16, marginBottom: 20 }}>
        <div className="card">
          <div className="card-title">
            {spot.find(s => s.code === activeIndex)?.name || '指数'} 近30日K线
          </div>
          {kline.length > 0 ? (
            <ResponsiveContainer width="100%" height={300}>
              <AreaChart data={kline}>
                <defs>
                  <linearGradient id="klineG" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor={kline[kline.length-1]?.close >= kline[0]?.open ? '#ef4444' : '#22c55e'} stopOpacity={0.3} />
                    <stop offset="100%" stopColor={kline[kline.length-1]?.close >= kline[0]?.open ? '#ef4444' : '#22c55e'} stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
                <XAxis dataKey="date" tick={{ fill: '#6b7280', fontSize: 10 }} tickFormatter={d => d?.slice(5) || ''} />
                <YAxis tick={{ fill: '#6b7280', fontSize: 10 }} domain={['auto', 'auto']} />
                <Tooltip contentStyle={{ background: '#1f2937', border: '1px solid #374151', borderRadius: 8 }}
                  labelStyle={{ color: '#9ca3af' }} />
                <Area type="monotone" dataKey="close" stroke={kline[kline.length-1]?.close >= kline[0]?.open ? '#ef4444' : '#22c55e'}
                  fill="url(#klineG)" strokeWidth={2} name="收盘" />
              </AreaChart>
            </ResponsiveContainer>
          ) : <p style={{ color: 'var(--text3)', textAlign: 'center', padding: 60 }}>K线数据加载中...</p>}
        </div>

        <div className="card">
          <div className="card-title">涨跌分布</div>
          <div style={{ display: 'flex', justifyContent: 'space-around', marginBottom: 16, padding: '12px 0' }}>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: 28, fontWeight: 'bold', color: 'var(--red)' }}>{summary.up || 0}</div>
              <div style={{ fontSize: 12, color: 'var(--text3)' }}>上涨</div>
            </div>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: 28, fontWeight: 'bold', color: 'var(--text3)' }}>{summary.flat || 0}</div>
              <div style={{ fontSize: 12, color: 'var(--text3)' }}>平盘</div>
            </div>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: 28, fontWeight: 'bold', color: 'var(--green)' }}>{summary.down || 0}</div>
              <div style={{ fontSize: 12, color: 'var(--text3)' }}>下跌</div>
            </div>
          </div>

          {/* 资金流向 */}
          <div style={{ padding: '0 0 8px', borderBottom: '1px solid var(--border)', marginBottom: 12 }}>
            <div style={{ fontSize: 12, color: 'var(--text3)', marginBottom: 4 }}>主力资金净流入</div>
            <div style={{ fontSize: 18, fontWeight: 'bold', color: (summary.total_flow || 0) >= 0 ? 'var(--red)' : 'var(--green)' }}>
              {fmt(summary.total_flow || 0)}
            </div>
          </div>

          {/* 资金TOP排名 */}
          <div style={{ fontSize: 12, color: 'var(--text3)', marginBottom: 8 }}>板块资金流入TOP5</div>
          {sectors.slice(0, 5).map(s => (
            <div key={s.name} style={{
              display: 'flex', justifyContent: 'space-between', alignItems: 'center',
              padding: '4px 0', borderBottom: '1px solid var(--border)', fontSize: 12,
            }}>
              <span>{s.name}</span>
              <span style={{ color: (s.flow || 0) >= 0 ? 'var(--red)' : 'var(--green)' }}>
                {fmt(s.flow || 0)}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* 行业板块热力图 */}
      <div className="card" style={{ marginBottom: 20 }}>
        <div className="card-title">行业轮动热力图（涨跌幅）</div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(110px, 1fr))', gap: 4 }}>
          {sectors.map(s => (
            <div key={s.code || s.name} style={{
              background: getColor(s.change_pct),
              borderRadius: 4,
              padding: '8px 6px',
              textAlign: 'center',
              color: '#fff',
              fontSize: 11,
              cursor: 'pointer',
              transition: 'opacity 0.15s',
            }} onMouseEnter={e => e.target.style.opacity = 0.8}
               onMouseLeave={e => e.target.style.opacity = 1}>
              <div style={{ fontWeight: 'bold', fontSize: 12, marginBottom: 2 }}>{s.name}</div>
              <div style={{ fontSize: 14, fontWeight: 'bold' }}>
                {s.change_pct >= 0 ? '+' : ''}{s.change_pct?.toFixed(2)}%
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* 自选股监控 */}
      <div className="card">
        <div className="card-title">自选股实时监控</div>
        <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
          <input value={watchInput} onChange={e => setWatchInput(e.target.value)}
            placeholder="逗号分隔股票代码" style={{
              flex: 1, padding: '6px 10px', background: 'var(--bg3)',
              border: '1px solid var(--border)', borderRadius: 6, color: 'var(--text)', fontSize: 13,
            }} />
          <button className="btn btn-sm" onClick={load}>刷新</button>
        </div>
        {watchlist.length === 0 ? (
          <p style={{ color: 'var(--text3)', textAlign: 'center', padding: 30 }}>输入股票代码添加监控</p>
        ) : (
          <table>
            <thead><tr><th>代码</th><th>名称</th><th>价格</th><th>涨跌</th><th>涨跌幅</th><th>成交额</th><th>换手率</th></tr></thead>
            <tbody>
              {watchlist.map(s => (
                <tr key={s.code}>
                  <td><span className="link" onClick={() => onSelect(s.code)}>{s.code}</span></td>
                  <td><span className="link" onClick={() => onSelect(s.code)}>{s.name}</span></td>
                  <td className={(s.pct_chg || s.change_pct || 0) >= 0 ? 'up' : 'down'} style={{ fontWeight: 'bold' }}>
                    {s.price?.toFixed(2)}
                  </td>
                  <td className={(s.pct_chg || s.change_pct || 0) >= 0 ? 'up' : 'down'}>
                    {s.change_amt ? (s.change_amt >= 0 ? '+' : '') + s.change_amt?.toFixed(2) : '-'}
                  </td>
                  <td className={(s.pct_chg || s.change_pct || 0) >= 0 ? 'up' : 'down'} style={{ fontWeight: 'bold' }}>
                    {(s.pct_chg || s.change_pct || 0) >= 0 ? '+' : ''}{(s.pct_chg || s.change_pct || 0)?.toFixed(2)}%
                  </td>
                  <td>{fmt(s.amount)}</td>
                  <td>{s.turnover?.toFixed(2)}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
