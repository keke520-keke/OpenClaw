import { useState, useEffect, useCallback } from 'react'

export default function TrailingStopPage() {
  const [config, setConfig] = useState({
    enabled: true,
    trigger_pct: 10.0,
    drawdown_pct: 3.0,
  })
  const [status, setStatus] = useState(null)
  const [loading, setLoading] = useState(false)

  const load = useCallback(async () => {
    try {
      const res = await fetch('/api/trailing/status').then(r => r.json())
      if (res.code === 0) setStatus(res.data)
    } catch (e) {
      console.error('加载失败:', e)
    }
  }, [])

  useEffect(() => { load() }, [load])

  const updateConfig = async () => {
    setLoading(true)
    try {
      const res = await fetch('/api/trailing/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config),
      }).then(r => r.json())
      if (res.code === 0) {
        setStatus(res.data)
        alert('配置已更新')
      }
    } catch (e) {
      alert('更新失败')
    }
    setLoading(false)
  }

  return (
    <div>
      <h2 className="page-title">追踪止盈 (Trailing Stop)</h2>

      {/* 状态卡片 */}
      <div className="card-grid" style={{ marginBottom: 16 }}>
        <div className="stat-card">
          <div className="stat-label">追踪止盈</div>
          <div className="stat-value" style={{ fontSize: 18, color: status?.enabled ? 'var(--green2)' : 'var(--text3)' }}>
            {status?.enabled ? '已开启' : '已关闭'}
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-label">触发阈值</div>
          <div className="stat-value" style={{ fontSize: 18 }}>{status?.trigger_pct || 10}%</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">回撤阈值</div>
          <div className="stat-value" style={{ fontSize: 18 }}>{status?.drawdown_pct || 3}%</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">激活持仓</div>
          <div className="stat-value" style={{ fontSize: 18 }}>{status?.active_positions || 0}只</div>
        </div>
      </div>

      {/* 配置面板 */}
      <div className="card" style={{ marginBottom: 16 }}>
        <div className="card-title">追踪止盈配置</div>
        <div style={{ display: 'flex', gap: 16, alignItems: 'center', flexWrap: 'wrap' }}>
          <div>
            <label style={{ fontSize: 12, color: 'var(--text3)' }}>启用追踪止盈</label>
            <div style={{ marginTop: 4 }}>
              <button 
                onClick={() => setConfig({ ...config, enabled: !config.enabled })}
                style={{
                  padding: '8px 16px',
                  background: config.enabled ? 'var(--green2)' : 'var(--bg3)',
                  color: config.enabled ? '#fff' : 'var(--text3)',
                  border: 'none',
                  borderRadius: 6,
                  cursor: 'pointer',
                }}
              >
                {config.enabled ? '已开启' : '已关闭'}
              </button>
            </div>
          </div>
          <div>
            <label style={{ fontSize: 12, color: 'var(--text3)' }}>触发阈值 (%)</label>
            <input
              type="number"
              value={config.trigger_pct}
              onChange={e => setConfig({ ...config, trigger_pct: parseFloat(e.target.value) || 10 })}
              style={inpStyle}
              min="1"
              max="50"
            />
          </div>
          <div>
            <label style={{ fontSize: 12, color: 'var(--text3)' }}>回撤阈值 (%)</label>
            <input
              type="number"
              value={config.drawdown_pct}
              onChange={e => setConfig({ ...config, drawdown_pct: parseFloat(e.target.value) || 3 })}
              style={inpStyle}
              min="0.5"
              max="20"
              step="0.5"
            />
          </div>
          <button 
            className="btn btn-primary" 
            onClick={updateConfig} 
            disabled={loading}
          >
            {loading ? '更新中...' : '保存配置'}
          </button>
        </div>
      </div>

      {/* 工作流程说明 */}
      <div className="card">
        <div className="card-title">工作流程</div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 16, fontSize: 13 }}>
          <div>
            <div style={{ fontWeight: 'bold', marginBottom: 4, color: 'var(--green2)' }}>1. 盈利触发</div>
            <div style={{ color: 'var(--text3)' }}>个股盈利达到{config.trigger_pct}%时，激活追踪状态</div>
          </div>
          <div>
            <div style={{ fontWeight: 'bold', marginBottom: 4, color: 'var(--green2)' }}>2. 记录高点</div>
            <div style={{ color: 'var(--text3)' }}>持续记录最高盈利和最高价格</div>
          </div>
          <div>
            <div style={{ fontWeight: 'bold', marginBottom: 4, color: 'var(--green2)' }}>3. 回撤卖出</div>
            <div style={{ color: 'var(--text3)' }}>从最高点回撤超过{config.drawdown_pct}%时，强制卖出</div>
          </div>
          <div>
            <div style={{ fontWeight: 'bold', marginBottom: 4, color: 'var(--green2)' }}>4. 锁定利润</div>
            <div style={{ color: 'var(--text3)' }}>企业微信推送卖出通知，锁定实际盈利</div>
          </div>
        </div>
      </div>

      {/* 活跃追踪状态 */}
      {status?.trailing_states && Object.keys(status.trailing_states).length > 0 && (
        <div className="card" style={{ marginTop: 16 }}>
          <div className="card-title">活跃追踪状态</div>
          <table>
            <thead>
              <tr>
                <th>股票代码</th>
                <th>最高盈利</th>
                <th>状态</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(status.trailing_states).map(([code, state]) => (
                <tr key={code}>
                  <td>{code}</td>
                  <td style={{ color: 'var(--green2)' }}>+{state.high_pnl?.toFixed(2)}%</td>
                  <td>
                    {state.triggered ? (
                      <span style={{ color: 'var(--yellow)' }}>追踪中</span>
                    ) : (
                      <span style={{ color: 'var(--text3)' }}>未激活</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

const inpStyle = {
  padding: '8px 12px',
  background: 'var(--bg3)',
  border: '1px solid var(--border)',
  borderRadius: 8,
  color: 'var(--text)',
  fontSize: 14,
  width: 80,
}
