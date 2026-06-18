import { useState, useEffect } from 'react'

export default function RiskSettings() {
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
      <h2 className="page-title">风控设置</h2>
      <div className="card-grid">
        <div className="stat-card">
          <div className="stat-label">风控状态</div>
          <div className="stat-value" style={{ color: risk.paused ? 'var(--red)' : 'var(--green2)' }}>
            {risk.paused ? '已暂停' : '正常'}
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-label">仓位上限</div>
          <div className="stat-value">{risk.position_limit_pct}%</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">单日回撤</div>
          <div className="stat-value">{risk.daily_max_dd}%</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">连续亏损</div>
          <div className="stat-value">{risk.consecutive_loss}/{risk.consecutive_loss_limit}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">黑天鹅阈值</div>
          <div className="stat-value">{risk.black_swan_threshold}%</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">总仓位</div>
          <div className="stat-value">{risk.total_position_pct}%</div>
        </div>
      </div>
    </div>
  )
}
