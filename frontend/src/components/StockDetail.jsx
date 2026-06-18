import { useState, useEffect } from 'react'
import { fmt } from '../hooks/useApi'

export default function StockDetail({ code, onBack }) {
  const [stock, setStock] = useState(null)
  const [kline, setKline] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    Promise.all([
      fetch(`/api/market/stock/${code}`).then(r => r.json()),
      fetch(`/api/market/kline/${code}`).then(r => r.json()),
    ]).then(([s, k]) => {
      setStock(s.data)
      setKline((k.data || []).slice(-30))
    }).catch(console.error).finally(() => setLoading(false))
  }, [code])

  if (loading) return <div className="loading">加载中...</div>
  if (!stock) return <div className="loading">未找到股票</div>

  const metrics = [
    ['今开', stock.open?.toFixed(2)], ['最高', stock.high?.toFixed(2)], ['最低', stock.low?.toFixed(2)],
    ['昨收', stock.pre_close?.toFixed(2)], ['换手率', stock.turnover_rate?.toFixed(2) + '%'],
    ['市盈率', stock.pe_ratio?.toFixed(2) || '-'], ['市净率', stock.pb_ratio?.toFixed(2) || '-'],
    ['总市值', fmt(stock.total_mv)], ['流通市值', fmt(stock.circ_mv)],
  ]

  return (
    <div>
      <button className="btn" onClick={onBack} style={{ marginBottom: 16 }}>返回列表</button>
      <div className="card">
        <div style={{ display: 'flex', alignItems: 'center', gap: 32, flexWrap: 'wrap' }}>
          <div>
            <div style={{ fontSize: 24, fontWeight: 'bold' }}>{stock.name}</div>
            <div style={{ color: 'var(--text3)' }}>{stock.code}</div>
          </div>
          <div style={{ marginLeft: 'auto', textAlign: 'right' }}>
            <div style={{ fontSize: 32, fontWeight: 'bold' }} className={stock.change_pct >= 0 ? 'up' : 'down'}>
              {stock.price?.toFixed(2)}
            </div>
            <div style={{ fontSize: 16 }} className={stock.change_pct >= 0 ? 'up' : 'down'}>
              {stock.change_pct >= 0 ? '+' : ''}{stock.change_pct?.toFixed(2)}%
            </div>
          </div>
        </div>
        <div className="card-grid" style={{ marginTop: 16 }}>
          {metrics.map(([label, value]) => (
            <div key={label} className="stat-card" style={{ textAlign: 'center' }}>
              <div className="stat-label">{label}</div>
              <div className="stat-value" style={{ fontSize: 16 }}>{value}</div>
            </div>
          ))}
        </div>
      </div>

      <div className="card">
        <div className="card-title">近期K线 (日线)</div>
        <div style={{ maxHeight: 400, overflow: 'auto' }}>
          <table>
            <thead><tr><th>日期</th><th>开盘</th><th>收盘</th><th>最高</th><th>最低</th><th>成交量</th><th>涨跌幅</th></tr></thead>
            <tbody>
              {[...kline].reverse().map((k, i) => (
                <tr key={i}>
                  <td>{k.date?.slice(0, 10)}</td>
                  <td>{k.open?.toFixed(2)}</td>
                  <td className={k.change_pct >= 0 ? 'up' : 'down'}>{k.close?.toFixed(2)}</td>
                  <td>{k.high?.toFixed(2)}</td>
                  <td>{k.low?.toFixed(2)}</td>
                  <td>{fmt(k.volume)}</td>
                  <td className={k.change_pct >= 0 ? 'up' : 'down'}>{k.change_pct >= 0 ? '+' : ''}{k.change_pct?.toFixed(2)}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
