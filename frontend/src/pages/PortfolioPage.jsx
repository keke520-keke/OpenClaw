import { useState, useEffect, useCallback } from 'react'
import { fmt } from '../hooks/useApi'
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, BarChart, Bar, CartesianGrid, XAxis, YAxis } from 'recharts'

const COLORS = ['#3b82f6', '#ef4444', '#22c55e', '#a855f7', '#f97316', '#eab308', '#6b7280', '#ec4899', '#14b8a6', '#6366f1']

export default function PortfolioPage() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const res = await fetch('/api/portfolio/overview')
      const d = await res.json()
      setData(d.data)
    } catch { }
    finally { setLoading(false) }
  }, [])

  useEffect(() => { load() }, [load])
  useEffect(() => { const t = setInterval(load, 30000); return () => clearInterval(t) }, [load])

  if (loading || !data) return <div className="loading">加载组合数据...</div>

  const positions = (data.assets || []).filter(a => a.code !== 'CASH')
  const cashAsset = (data.assets || []).find(a => a.code === 'CASH') || { value: data.cash }
  const pieData = (data.assets || []).map(a => ({ name: a.name, value: a.value }))
  const limits = data.limits || []

  return (
    <div>
      <h2 className="page-title">组合管理</h2>

      {/* 概览卡片 */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(6, 1fr)', gap: 12, marginBottom: 20 }}>
        <BigCard label="总资产" value={`${(data.total_equity / 10000).toFixed(2)}万`} />
        <BigCard label="现金" value={`${(data.cash / 10000).toFixed(2)}万`}
          sub={`${(data.cash / data.total_equity * 100).toFixed(1)}%`} />
        <BigCard label="持仓市值" value={`${(data.market_value / 10000).toFixed(2)}万`}
          sub={`${data.position_count}只`} />
        <BigCard label="VaR(95%)" value={`${data.risk?.var_95}%`}
          color="var(--red)" sub="单日最大损失5%概率" />
        <BigCard label="最大回撤" value={`${data.risk?.max_drawdown}%`}
          color={data.risk?.max_drawdown < -5 ? 'var(--red)' : 'var(--text)'} />
        <BigCard label="波动率" value={`${data.risk?.volatility}%`}
          sub="年化估算" />
      </div>

      {/* 资产配置 + 持仓详情 */}
      <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 1.8fr', gap: 16, marginBottom: 20 }}>
        <div className="card" style={{ padding: '20px 10px' }}>
          <div className="card-title">资产配置</div>
          {pieData.length > 0 ? (
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', width: '100%' }}>
              <div style={{ width: '100%', maxWidth: 280, height: 280 }}>
                <ResponsiveContainer width="100%" height={280}>
                  <PieChart>
                    <Pie data={pieData} cx="50%" cy="50%" innerRadius={40} outerRadius={90}
                      dataKey="value" 
                      label={false}
                      labelLine={false}>
                      {pieData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                    </Pie>
                    <Tooltip 
                      formatter={(value, name) => [fmt(value), name]}
                      contentStyle={{ background: '#1a1a24', border: '1px solid #2a2a35', borderRadius: 8, color: '#e8e8f0', padding: '8px 12px' }} 
                    />
                  </PieChart>
                </ResponsiveContainer>
              </div>
              {/* 图例 - 两列布局 */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '6px 12px', marginTop: 8, width: '100%' }}>
                {pieData.slice(0, 6).map((item, i) => (
                  <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 11 }}>
                    <div style={{ width: 8, height: 8, borderRadius: 2, background: COLORS[i % COLORS.length], flexShrink: 0 }} />
                    <span style={{ color: 'var(--text2)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {item.name}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          ) : <p style={{ color: 'var(--text3)', textAlign: 'center', padding: 60 }}>无持仓</p>}
        </div>

        <div className="card">
          <div className="card-title">持仓明细</div>
          {positions.length === 0 ? (
            <p style={{ color: 'var(--text3)', textAlign: 'center', padding: 40 }}>无持仓，去「纸盘」下单</p>
          ) : (
            <div style={{ overflowX: 'auto' }}>
              <table>
                <thead><tr>
                  <th>代码</th><th>名称</th><th>数量</th><th>成本</th><th>现价</th>
                  <th>市值</th><th>权重</th><th>盈亏</th><th>盈亏%</th>
                </tr></thead>
                <tbody>
                  {positions.map(p => (
                    <tr key={p.code}>
                      <td>{p.code}</td><td>{p.name}</td><td>{p.shares}股</td>
                      <td>{p.avg_cost?.toFixed(2)}</td><td>{p.current_price?.toFixed(2)}</td>
                      <td>{fmt(p.value)}</td>
                      <td>{p.weight}%</td>
                      <td className={p.pnl >= 0 ? 'up' : 'down'}>{fmt(p.pnl)}</td>
                      <td className={p.pnl_pct >= 0 ? 'up' : 'down'}>{p.pnl_pct >= 0 ? '+' : ''}{p.pnl_pct?.toFixed(2)}%</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>

      {/* 风险限额 */}
      <div className="card">
        <div className="card-title">风险限额告警</div>
        {limits.length === 0 ? (
          <p style={{ color: 'var(--green2)', textAlign: 'center', padding: 20 }}>所有风控指标正常</p>
        ) : (
          <table>
            <thead><tr><th>指标</th><th>当前值</th><th>限额</th><th>状态</th></tr></thead>
            <tbody>
              {limits.map(l => (
                <tr key={l.name}>
                  <td>{l.name}</td>
                  <td style={{ fontWeight: 'bold', color: l.status === 'danger' ? 'var(--red)' : l.status === 'warning' ? 'var(--yellow)' : 'var(--text)' }}>
                    {l.current}%
                  </td>
                  <td>{l.limit}%</td>
                  <td>
                    <span style={{
                      padding: '2px 8px', borderRadius: 4, fontSize: 11, fontWeight: 'bold',
                      background: l.status === 'danger' ? 'rgba(239,68,68,0.1)' : l.status === 'warning' ? 'rgba(234,179,8,0.1)' : 'rgba(34,197,94,0.1)',
                      color: l.status === 'danger' ? 'var(--red)' : l.status === 'warning' ? 'var(--yellow)' : 'var(--green2)',
                    }}>
                      {l.status === 'danger' ? '超限' : l.status === 'warning' ? '警告' : '正常'}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
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
