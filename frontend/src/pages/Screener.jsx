import { useState, useMemo } from 'react'
import { fmt } from '../hooks/useApi'

const STRATEGIES = [
  { key: 'breakout', name: '放量突破', desc: '涨幅>1% + 换手>2%', endpoint: '/api/stock/breakout' },
  { key: 'bluechip', name: '低估值蓝筹', desc: 'PE<30 + 价格<30', endpoint: '/api/stock/bluechip' },
  { key: 'limitup', name: '涨停板', desc: '涨幅≥9%', endpoint: '/api/stock/limitup' },
  { key: 'active', name: '高换手活跃', desc: '换手率>5%', endpoint: '/api/stock/active' },
  { key: 'technical', name: '技术选股', desc: '多因子打分', endpoint: '/api/screener/technical' },
  { key: 'scoring', name: '多因子打分', desc: '综合评分排序', endpoint: '/api/scoring/top' },
]

export default function Screener({ onSelect }) {
  const [active, setActive] = useState(null)
  const [result, setResult] = useState([])
  const [loading, setLoading] = useState(false)
  const [sortBy, setSortBy] = useState('amount')
  const [sortDir, setSortDir] = useState(-1)

  const run = async (key, endpoint) => {
    setActive(key)
    setLoading(true)
    try {
      const res = await fetch(endpoint)
      const d = await res.json()
      if (d.code === 0) {
        setResult(d.data || [])
      }
    } catch (e) { console.error(e) }
    finally { setLoading(false) }
  }

  const sorted = useMemo(() => {
    const arr = [...result]
    arr.sort((a, b) => ((b[sortBy] || 0) - (a[sortBy] || 0)) * sortDir)
    return arr
  }, [result, sortBy, sortDir])

  const toggleSort = (key) => {
    if (sortBy === key) setSortDir(d => -d)
    else { setSortBy(key); setSortDir(-1) }
  }

  return (
    <div>
      <h2 className="page-title">选股器</h2>
      <div style={{ display: 'flex', gap: 20 }}>
        <div style={{ minWidth: 200 }}>
          <div className="card-title" style={{ marginBottom: 12 }}>选股策略</div>
          {STRATEGIES.map((s) => (
            <div key={s.key}
              className="stat-card"
              style={{ marginBottom: 8, cursor: 'pointer', border: active === s.key ? '1px solid var(--blue)' : '1px solid transparent' }}
              onClick={() => run(s.key, s.endpoint)}
            >
              <div style={{ fontWeight: 'bold', marginBottom: 4 }}>{s.name}</div>
              <div style={{ fontSize: 12, color: 'var(--text3)' }}>{s.desc}</div>
            </div>
          ))}
        </div>

        <div style={{ flex: 1 }}>
          {!active ? (
            <div className="loading">选择左侧策略开始选股</div>
          ) : loading ? (
            <div className="loading">扫描中...</div>
          ) : sorted.length === 0 ? (
            <div className="loading">当前条件无匹配结果</div>
          ) : (
            <>
              <div style={{ marginBottom: 8, color: 'var(--text2)' }}>
                筛选出 <strong style={{ color: 'var(--blue)' }}>{sorted.length}</strong> 只
              </div>
              <table>
                <thead>
                  <tr>
                    <th>代码</th><th>名称</th>
                    <th>价格</th>
                    <th>涨跌幅</th>
                    <th>成交额</th>
                    <th>换手率</th>
                    {active === 'scoring' && <th>综合评分</th>}
                    {active === 'scoring' && <th>评级</th>}
                  </tr>
                </thead>
                <tbody>
                  {sorted.map((r) => (
                    <tr key={r.code}>
                      <td>{r.code}</td>
                      <td><span className="link" onClick={() => onSelect(r.code)}>{r.name}</span></td>
                      <td>{r.price?.toFixed(2)}</td>
                      <td className={(r.pct_chg || r.change_pct || 0) >= 0 ? 'up' : 'down'}>
                        {(r.pct_chg || r.change_pct || 0) >= 0 ? '+' : ''}{(r.pct_chg || r.change_pct || 0)?.toFixed(2)}%
                      </td>
                      <td>{fmt(r.amount)}</td>
                      <td>{(r.turnover || r.turnover_rate || 0)?.toFixed(2)}%</td>
                      {active === 'scoring' && <td style={{ fontWeight: 'bold' }}>{r.composite_score?.toFixed(1)}</td>}
                      {active === 'scoring' && <td><span style={{ 
                        padding: '2px 8px', borderRadius: 4, fontSize: 11,
                        background: r.grade === 'A' ? 'rgba(34,197,94,0.2)' : r.grade === 'B' ? 'rgba(59,130,246,0.2)' : 'rgba(156,163,175,0.2)',
                        color: r.grade === 'A' ? 'var(--green2)' : r.grade === 'B' ? 'var(--blue)' : 'var(--text2)'
                      }}>{r.grade}</span></td>}
                    </tr>
                  ))}
                </tbody>
              </table>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
