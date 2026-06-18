import { useState, useEffect, useCallback } from 'react'
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid,
  LineChart, Line, Legend, Cell
} from 'recharts'

export default function FactorsPage() {
  const [factors, setFactors] = useState([])
  const [icSeries, setIcSeries] = useState([])
  const [activeCat, setActiveCat] = useState('')
  const [tab, setTab] = useState('list')
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const res = await fetch('/api/factors/full-list')
      const d = await res.json()
      setFactors(d.factors || [])
      setIcSeries(d.ic_series || [])
    } catch { }
    finally { setLoading(false) }
  }, [])

  useEffect(() => { load() }, [load])

  if (loading) return <div className="loading">加载因子库...</div>

  const filtered = activeCat ? factors.filter(f => f.category === activeCat) : factors
  const categories = { 技术: 0, 财务: 0, 另类: 0 }
  factors.forEach(f => { if (categories[f.category] !== undefined) categories[f.category]++ })

  // IC排名（按IC均值降序）
  const icRank = [...factors].sort((a, b) => (b.ic_mean || 0) - (a.ic_mean || 0))

  return (
    <div>
      <h2 className="page-title">因子研究</h2>

      {/* 分类统计 */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12, marginBottom: 20 }}>
        <div className="stat-card" style={{ textAlign: 'center' }}>
          <div className="stat-label">总因子数</div>
          <div className="stat-value" style={{ fontSize: 28, color: 'var(--blue)' }}>{factors.length}</div>
        </div>
        {Object.entries(categories).map(([name, count]) => (
          <div key={name} className="stat-card" style={{ textAlign: 'center', cursor: 'pointer',
            border: activeCat === name ? '1px solid var(--blue)' : '1px solid transparent' }}
            onClick={() => setActiveCat(activeCat === name ? '' : name)}>
            <div className="stat-label">{name}因子</div>
            <div className="stat-value" style={{ fontSize: 28,
              color: name === '技术' ? 'var(--blue)' : name === '财务' ? 'var(--green)' : 'var(--purple)' }}>
              {count}
            </div>
          </div>
        ))}
      </div>

      {/* Tab */}
      <div className="tab-bar" style={{ marginBottom: 16 }}>
        {['list', 'ic_rank', 'ic_chart', 'layer'].map(t => (
          <button key={t} className={`tab-btn ${tab === t ? 'active' : ''}`} onClick={() => setTab(t)}>
            {{ list: '因子列表', ic_rank: 'IC排名', ic_chart: 'IC时序', layer: '分层收益' }[t]}
          </button>
        ))}
      </div>

      {/* 因子列表 */}
      {tab === 'list' && (
        <div className="card">
          <div className="card-title">因子列表 ({filtered.length})</div>
          <div style={{ maxHeight: 500, overflow: 'auto' }}>
            <table>
              <thead><tr><th>名称</th><th>分类</th><th>说明</th><th>IC均值</th><th>IR</th></tr></thead>
              <tbody>
                {filtered.map(f => (
                  <tr key={f.name}>
                    <td style={{ fontFamily: 'monospace', color: 'var(--blue)' }}>{f.name}</td>
                    <td><span style={{
                      padding: '2px 8px', borderRadius: 4, fontSize: 11,
                      background: f.category === '技术' ? 'rgba(59,130,246,0.1)' : f.category === '财务' ? 'rgba(34,197,94,0.1)' : 'rgba(168,85,247,0.1)',
                      color: f.category === '技术' ? 'var(--blue)' : f.category === '财务' ? 'var(--green)' : 'var(--purple)',
                    }}>{f.category}</span></td>
                    <td style={{ color: 'var(--text2)', fontSize: 13 }}>{f.desc}</td>
                    <td style={{ fontWeight: 'bold', color: (f.ic_mean || 0) > 0.03 ? 'var(--green2)' : 'var(--text)' }}>
                      {(f.ic_mean || 0).toFixed(3)}
                    </td>
                    <td>{(f.ir || 0).toFixed(2)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* IC排名 */}
      {tab === 'ic_rank' && (
        <div className="card">
          <div className="card-title">IC排名（按均值降序）</div>
          <ResponsiveContainer width="100%" height={400}>
            <BarChart data={icRank.slice(0, 20)} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis type="number" tick={{ fill: '#9ca3af', fontSize: 11 }}
                tickFormatter={v => v.toFixed(3)} />
              <YAxis dataKey="name" type="category" tick={{ fill: '#9ca3af', fontSize: 11 }} width={100} />
              <Tooltip contentStyle={{ background: '#1f2937', border: '1px solid #374151', borderRadius: 8 }}
                formatter={v => v.toFixed(4)} />
              <Bar dataKey="ic_mean" name="IC均值" radius={[0, 4, 4, 0]}>
                {icRank.slice(0, 20).map((f, i) => (
                  <Cell key={i} fill={f.category === '财务' ? '#22c55e' : f.category === '另类' ? '#a855f7' : '#3b82f6'} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* IC时序 */}
      {tab === 'ic_chart' && (
        <div className="card">
          <div className="card-title">IC时序（主要因子月度IC）</div>
          {icSeries.length > 0 ? (
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', minWidth: 600 }}>
                <thead>
                  <tr>
                    <th>月份</th>
                    <th style={{ color: '#22c55e' }}>F_ROE</th>
                    <th style={{ color: '#3b82f6' }}>F_PE</th>
                    <th style={{ color: '#a855f7' }}>T_RSI14</th>
                    <th style={{ color: '#f97316' }}>T_J</th>
                    <th style={{ color: '#eab308' }}>T_MA5</th>
                  </tr>
                </thead>
                <tbody>
                  {icSeries.slice(-12).map((item, i) => (
                    <tr key={i}>
                      <td>{item.month}</td>
                      <td style={{ color: item.F_ROE > 0 ? 'var(--green2)' : 'var(--red)' }}>{(item.F_ROE || 0).toFixed(4)}</td>
                      <td style={{ color: item.F_PE > 0 ? 'var(--green2)' : 'var(--red)' }}>{(item.F_PE || 0).toFixed(4)}</td>
                      <td style={{ color: item.T_RSI14 > 0 ? 'var(--green2)' : 'var(--red)' }}>{(item.T_RSI14 || 0).toFixed(4)}</td>
                      <td style={{ color: item.T_J > 0 ? 'var(--green2)' : 'var(--red)' }}>{(item.T_J || 0).toFixed(4)}</td>
                      <td style={{ color: item.T_MA5 > 0 ? 'var(--green2)' : 'var(--red)' }}>{(item.T_MA5 || 0).toFixed(4)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div style={{ textAlign: 'center', padding: 60, color: 'var(--text3)' }}>暂无IC时序数据</div>
          )}
        </div>
      )}

      {/* 分层收益 */}
      {tab === 'layer' && (
        <div className="card">
          <div className="card-title">分层收益（TOP层 vs BOTTOM层）</div>
          <ResponsiveContainer width="100%" height={400}>
            <BarChart data={icRank.slice(0, 20)}>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis dataKey="name" tick={{ fill: '#9ca3af', fontSize: 9 }} angle={-45} textAnchor="end" height={60} />
              <YAxis tick={{ fill: '#9ca3af', fontSize: 11 }} tickFormatter={v => `${v}%`} />
              <Tooltip contentStyle={{ background: '#1f2937', border: '1px solid #374151', borderRadius: 8 }}
                formatter={v => `${v}%`} />
              <Legend wrapperStyle={{ fontSize: 12 }} />
              <Bar dataKey="layer1" name="TOP层收益%" fill="#ef4444" radius={[4, 4, 0, 0]} />
              <Bar dataKey="layer5" name="BOTTOM层收益%" fill="#22c55e" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  )
}
