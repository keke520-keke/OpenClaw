import { useState, useEffect } from 'react'

export default function Monitor() {
  const [risk, setRisk] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch('/api/risk/status')
      .then(r => r.json())
      .then(d => { if (d.code === 0) setRisk(d.data) })
      .catch(e => console.error(e))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <div className="loading">加载中...</div>
  if (!risk) return <div className="loading">加载失败</div>

  return (
    <div>
      <h2 className="page-title">市场监控</h2>
      <div className="card-grid">
        <div className="stat-card">
          <div className="stat-label">风控状态</div>
          <div className="stat-value" style={{ color: risk.paused ? 'var(--red)' : 'var(--green2)' }}>
            {risk.paused ? '已暂停' : '正常'}
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-label">总仓位</div>
          <div className="stat-value">{risk.total_position_pct}%</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">持仓数</div>
          <div className="stat-value">{risk.today_trades ? Object.keys(risk.today_trades).length : 0}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">风控告警</div>
          <div className="stat-value">{risk.alerts_count}</div>
        </div>
      </div>
    </div>
  )
}
