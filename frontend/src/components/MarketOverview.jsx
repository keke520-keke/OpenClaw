import { useApi } from '../hooks/useApi'

export default function MarketOverview() {
  const { data, loading } = useApi('/market/overview')
  if (loading) return <div className="loading">加载大盘...</div>
  return (
    <div className="card-grid">
      {data?.map((idx) => (
        <div key={idx.code} className="stat-card" style={{ textAlign: 'center' }}>
          <div className="stat-label">{idx.name}</div>
          <div className={`stat-value ${idx.change_pct >= 0 ? 'up' : 'down'}`}>
            {idx.price?.toFixed(2)}
          </div>
          <div className={`stat-change ${idx.change_pct >= 0 ? 'up' : 'down'}`}>
            {idx.change_pct >= 0 ? '+' : ''}{idx.change_pct?.toFixed(2)}%
          </div>
        </div>
      ))}
    </div>
  )
}
