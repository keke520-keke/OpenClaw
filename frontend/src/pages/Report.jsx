import { useState, useEffect, useCallback } from 'react'
import { fmt } from '../hooks/useApi'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Cell, PieChart, Pie, Legend, AreaChart, Area, Brush, ReferenceLine, ReferenceDot } from 'recharts'

export default function Report() {
  const [data, setData] = useState(null)
  const [tradeList, setTradeList] = useState([])
  const [stratStats, setStratStats] = useState({})
  const [chartData, setChartData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [tab, setTab] = useState('overview')
  const [filterSide, setFilterSide] = useState('all')
  const [filterStrategy, setFilterStrategy] = useState('')
  const [filterPnl, setFilterPnl] = useState('')
  const [sortBy, setSortBy] = useState('time')
  const [sortDir, setSortDir] = useState(-1)

  const toggleSort = (key) => {
    if (sortBy === key) setSortDir(d => -d)
    else { setSortBy(key); setSortDir(-1) }
  }

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const [s, t, c] = await Promise.all([
        fetch('/api/report/summary').then(r => r.json()),
        fetch('/api/report/trade-list').then(r => r.json()),
        fetch('/api/report/chart-data').then(r => r.json()),
      ])
      setData(s.data)
      setTradeList(t.data || [])
      setStratStats(t.strategies || {})
      setChartData(c.data)
    } catch { }
    finally { setLoading(false) }
  }, [])

  useEffect(() => { load() }, [load])

  if (loading) return <div className="loading">加载复盘报告...</div>
  if (!data) return <div className="loading">暂无数据</div>

  const d = data
  const isUp = d.total_return_pct >= 0

  // 计算关键事件标记
  const events = []
  if (chartData) {
    // 1. 买卖事件（从 tradeList）
    tradeList.forEach(t => {
      if (t.side === 'sell') {
        const label = t.pnl >= 0 ? `止盈${t.strategy}` : `止损${t.strategy}`
        events.push({ date: t.time?.slice(0, 10), value: 0, label, type: t.pnl >= 0 ? 'tp' : 'sl' })
      } else {
        events.push({ date: t.time?.slice(0, 10), value: 0, label: `买入${t.strategy}`, type: 'buy' })
      }
    })
    // 2. 大回撤事件（dd < -5%）
    chartData.drawdown_curve?.forEach(dd => {
      if (dd.dd <= -5) {
        events.push({ date: dd.date, value: dd.dd, label: `回撤${dd.dd}%`, type: 'dd' })
      }
    })
    // 3. 去重同日事件
    const seen = new Set()
    const uniqueEvents = []
    events.forEach(e => {
      const key = `${e.date}_${e.type}`
      if (!seen.has(key)) { seen.add(key); uniqueEvents.push(e) }
    })
    uniqueEvents.sort((a, b) => a.date?.localeCompare(b.date))
  }

  // 构建带事件标记的净值数据
  const eqWithEvents = (chartData?.equity_curve || []).map(pt => {
    const dayEvents = (events || []).filter(e => e.date === pt.date)
    return { ...pt, events: dayEvents }
  })

  // 交易盈亏分布图数据
  const pnlDist = d.trade_details?.map((t, i) => ({
    name: `${t.name}`,
    pnl: t.pnl,
    fill: t.pnl >= 0 ? '#ef4444' : '#22c55e',
  })) || []

  // 计算持仓天数 + 筛选 + 排序
  const enrichedTrades = tradeList.map(t => {
    if (t.side === 'sell') {
      const buyTime = tradeList.find(b => b.code === t.code && b.side === 'buy' && b.time < t.time)
      if (buyTime) {
        const days = Math.round((new Date(t.time) - new Date(buyTime.time)) / 86400000)
        return { ...t, hold_days: Math.max(days, 1) }
      }
    }
    return { ...t, hold_days: null }
  })

  const allStrategies = [...new Set(enrichedTrades.map(t => t.strategy).filter(Boolean))]

  const filteredTrades = enrichedTrades.filter(t => {
    if (filterSide !== 'all' && t.side !== filterSide) return false
    if (filterStrategy && t.strategy !== filterStrategy) return false
    if (filterPnl === 'profit' && t.side === 'sell' && t.pnl <= 0) return false
    if (filterPnl === 'loss' && t.side === 'sell' && t.pnl >= 0) return false
    if (filterPnl === 'tp' && !t.is_take_profit) return false
    if (filterPnl === 'sl' && !t.is_stop_loss) return false
    return true
  })

  const sortedTrades = [...filteredTrades].sort((a, b) => {
    const av = a[sortBy] ?? 0
    const bv = b[sortBy] ?? 0
    if (typeof av === 'string') return av.localeCompare(bv) * sortDir
    return (av - bv) * sortDir
  })

  // 持仓饼图数据
  const posPie = d.positions?.map(p => ({
    name: p.name,
    value: p.market_value,
  })) || []
  if (d.cash > 0) posPie.push({ name: '现金', value: d.cash })
  const pieColors = ['#3b82f6', '#ef4444', '#22c55e', '#a855f7', '#f97316', '#eab308', '#6b7280', '#ec4899', '#14b8a6', '#6366f1']

  return (
    <div>
      <h2 className="page-title">交易复盘</h2>

      {/* 核心指标 */}
      <div className="card-grid" style={{ marginBottom: 16 }}>
        <Stat label="初始资金" value="100万" />
        <Stat label="当前总资产" value={`${(d.current_equity / 10000).toFixed(2)}万`}
          sub={`现金${(d.cash / 10000).toFixed(2)}万 | 持仓${(d.market_value / 10000).toFixed(2)}万`} />
        <Stat label="累计收益率" value={`${d.total_return_pct >= 0 ? '+' : ''}${d.total_return_pct}%`}
          color={isUp ? 'var(--red)' : 'var(--green)'}
          sub={`年化 ${d.annual_return_pct >= 0 ? '+' : ''}${d.annual_return_pct}%`} />
        <Stat label="最大回撤" value={`${d.max_drawdown_pct}%`}
          color="var(--red)" sub={`${d.trading_days}个交易日`} />
        <Stat label="胜率" value={`${d.win_rate_pct}%`}
          color={d.win_rate_pct >= 50 ? 'var(--green2)' : 'var(--red)'}
          sub={`${d.win_trades}胜 ${d.loss_trades}负`} />
        <Stat label="盈亏比" value={d.profit_loss_ratio?.toFixed(2)}
          color={d.profit_loss_ratio >= 1 ? 'var(--green2)' : 'var(--red)'}
          sub={`均盈${fmt(d.avg_win)} 均亏${fmt(d.avg_loss)}`} />
        <Stat label="总佣金" value={`${d.total_commission?.toFixed(2)}元`}
          sub={`占比${d.commission_pct}%`} />
        <Stat label="交易笔数" value={`${d.total_trades}笔`}
          sub={`买${d.buy_trades} 卖${d.sell_trades}`} />
      </div>

      <div className="tab-bar">
        {['overview', 'trades', 'chart', 'positions'].map(t => (
          <button key={t} className={`tab-btn ${tab === t ? 'active' : ''}`} onClick={() => setTab(t)}>
            {{ overview: '概览', trades: '交易明细', chart: '曲线图', positions: '持仓分析' }[t]}
          </button>
        ))}
      </div>

      {/* 概览 */}
      {tab === 'overview' && (
        <>
          {/* 核心指标：大卡片行 */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 12, marginBottom: 16 }}>
            <div className="stat-card" style={{ textAlign: 'center', padding: 20 }}>
              <div className="stat-label" style={{ fontSize: 13, marginBottom: 8 }}>总收益率</div>
              <div className="stat-value" style={{ fontSize: 28, fontWeight: 'bold', color: d.total_return_pct >= 0 ? 'var(--red)' : 'var(--green)' }}>
                {d.total_return_pct >= 0 ? '+' : ''}{d.total_return_pct}%
              </div>
              <div style={{ fontSize: 12, color: 'var(--text3)', marginTop: 4 }}>{fmt(d.total_realized_pnl + d.total_unrealized_pnl)}</div>
            </div>
            <div className="stat-card" style={{ textAlign: 'center', padding: 20 }}>
              <div className="stat-label" style={{ fontSize: 13, marginBottom: 8 }}>年化收益率</div>
              <div className="stat-value" style={{ fontSize: 28, fontWeight: 'bold', color: d.annual_return_pct >= 0 ? 'var(--red)' : 'var(--green)' }}>
                {d.annual_return_pct >= 0 ? '+' : ''}{d.annual_return_pct}%
              </div>
              <div style={{ fontSize: 12, color: 'var(--text3)', marginTop: 4 }}>{d.trading_days}个交易日</div>
            </div>
            <div className="stat-card" style={{ textAlign: 'center', padding: 20 }}>
              <div className="stat-label" style={{ fontSize: 13, marginBottom: 8 }}>最大回撤</div>
              <div className="stat-value" style={{ fontSize: 28, fontWeight: 'bold', color: 'var(--red)' }}>
                {d.max_drawdown_pct}%
              </div>
              <div style={{ fontSize: 12, color: 'var(--text3)', marginTop: 4 }}>Peak-to-Trough 标准计算</div>
            </div>
            <div className="stat-card" style={{ textAlign: 'center', padding: 20 }}>
              <div className="stat-label" style={{ fontSize: 13, marginBottom: 8 }}>夏普比率</div>
              <div className="stat-value" style={{ fontSize: 28, fontWeight: 'bold', color: d.sharpe_ratio >= 1 ? 'var(--green2)' : d.sharpe_ratio >= 0 ? 'var(--text)' : 'var(--red)' }}>
                {d.sharpe_ratio}
              </div>
              <div style={{ fontSize: 12, color: 'var(--text3)', marginTop: 4 }}>Calmar {d.calmar_ratio} | Sortino {d.sortino_ratio}</div>
            </div>
            <div className="stat-card" style={{ textAlign: 'center', padding: 20 }}>
              <div className="stat-label" style={{ fontSize: 13, marginBottom: 8 }}>胜率 / 盈亏比</div>
              <div className="stat-value" style={{ fontSize: 28, fontWeight: 'bold', color: d.win_rate_pct >= 50 ? 'var(--green2)' : 'var(--red)' }}>
                {d.win_rate_pct}%
              </div>
              <div style={{ fontSize: 12, color: 'var(--text3)', marginTop: 4 }}>{d.win_trades}胜{d.loss_trades}负 | {d.profit_loss_ratio?.toFixed(2)} | 均持{d.avg_hold_days}天</div>
            </div>
          </div>

          {/* 下方：持仓饼图 + 策略对比 */}
          <div className="grid-2">
            <div className="card">
              <div className="card-title">持仓分布</div>
              {posPie.length > 0 ? (
                <ResponsiveContainer width="100%" height={240}>
                  <PieChart>
                    <Pie data={posPie} cx="50%" cy="50%" innerRadius={45} outerRadius={90}
                      dataKey="value" label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                      labelLine={false}>
                      {posPie.map((_, i) => <Cell key={i} fill={pieColors[i % pieColors.length]} />)}
                    </Pie>
                    <Tooltip formatter={v => fmt(v)} contentStyle={{ background: '#1f2937', border: '1px solid #374151', borderRadius: 8 }} />
                  </PieChart>
                </ResponsiveContainer>
              ) : <p style={{ color: 'var(--text3)', textAlign: 'center', padding: 60 }}>无持仓</p>}
            </div>
            <div className="card">
              <div className="card-title">策略表现对比</div>
              {chartData?.strategy_pnl?.length > 0 ? (
                <ResponsiveContainer width="100%" height={240}>
                  <BarChart data={chartData.strategy_pnl} layout="vertical">
                    <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                    <XAxis type="number" tick={{ fill: '#9ca3af', fontSize: 11 }} tickFormatter={v => fmt(v)} />
                    <YAxis dataKey="name" type="category" tick={{ fill: '#9ca3af', fontSize: 12 }} width={80} />
                    <Tooltip contentStyle={{ background: '#1f2937', border: '1px solid #374151', borderRadius: 8 }}
                      formatter={v => fmt(v)} />
                    <Bar dataKey="pnl" name="盈亏" radius={[0, 4, 4, 0]}>
                      {chartData.strategy_pnl.map((entry, i) => (
                        <Cell key={i} fill={entry.pnl >= 0 ? '#ef4444' : '#22c55e'} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <div style={{ textAlign: 'center', padding: 60, color: 'var(--text3)' }}>
                  <div style={{ fontSize: 36, marginBottom: 12 }}>&#128202;</div>
                  <div>卖出交易后显示策略对比</div>
                </div>
              )}
            </div>
          </div>
        </>
      )}

      {/* 交易明细 */}
      {tab === 'trades' && (
        <>
          {/* 策略统计 */}
          {Object.keys(stratStats).length > 0 && (
            <div className="card" style={{ marginBottom: 16 }}>
              <div className="card-title">策略收益统计</div>
              <table>
                <thead><tr><th>策略</th><th>笔数</th><th>买</th><th>卖</th><th>胜率</th><th>总盈亏</th></tr></thead>
                <tbody>
                  {Object.entries(stratStats).map(([name, s]) => (
                    <tr key={name}>
                      <td style={{ fontWeight: 'bold' }}>{name}</td>
                      <td>{s.count}</td><td>{s.buy}</td><td>{s.sell}</td>
                      <td style={{ color: s.win_rate >= 50 ? 'var(--green2)' : 'var(--red)' }}>{s.win_rate}%</td>
                      <td className={s.total_pnl >= 0 ? 'up' : 'down'}>{fmt(s.total_pnl)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* 筛选器 */}
          <div className="card" style={{ marginBottom: 16, padding: '12px 16px' }}>
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
              <span style={{ fontSize: 12, color: 'var(--text3)', minWidth: 36 }}>方向</span>
              {[['all','全部'],['buy','买入'],['sell','卖出']].map(([v, l]) => (
                <button key={v} className={`btn btn-sm ${filterSide === v ? 'btn-primary' : ''}`}
                  onClick={() => setFilterSide(v)} style={{ padding: '3px 10px' }}>{l}</button>
              ))}
              <span style={{ fontSize: 12, color: 'var(--text3)', minWidth: 36, marginLeft: 12 }}>盈亏</span>
              {[['','全部'],['profit','盈利'],['loss','亏损'],['tp','止盈'],['sl','止损']].map(([v, l]) => (
                <button key={v} className={`btn btn-sm ${filterPnl === v ? 'btn-primary' : ''}`}
                  onClick={() => setFilterPnl(v)} style={{ padding: '3px 10px' }}>{l}</button>
              ))}
              {allStrategies.length > 1 && <>
                <span style={{ fontSize: 12, color: 'var(--text3)', minWidth: 36, marginLeft: 12 }}>策略</span>
                <select value={filterStrategy} onChange={e => setFilterStrategy(e.target.value)}
                  style={{ background: 'var(--bg3)', border: '1px solid var(--border)', color: 'var(--text)', padding: '3px 8px', borderRadius: 4, fontSize: 12 }}>
                  <option value="">全部</option>
                  {allStrategies.map(s => <option key={s} value={s}>{s}</option>)}
                </select>
              </>}
            </div>
          </div>

          {/* 全部交易记录 */}
          <div className="card">
            <div className="card-title">全部交易记录（共{filteredTrades.length}笔）</div>
            {filteredTrades.length === 0 ? (
              <p style={{ color: 'var(--text3)', textAlign: 'center', padding: 40 }}>无匹配记录</p>
            ) : (
              <div style={{ overflowX: 'auto' }}>
                <table>
                  <thead><tr>
                    <th style={{ cursor: 'pointer' }} onClick={() => toggleSort('time')}>
                      时间{sortBy === 'time' ? (sortDir > 0 ? '↑' : '↓') : ''}
                    </th>
                    <th>代码</th><th>名称</th>
                    <th>方向</th>
                    <th style={{ cursor: 'pointer' }} onClick={() => toggleSort('strategy')}>
                      策略{sortBy === 'strategy' ? (sortDir > 0 ? '↑' : '↓') : ''}
                    </th>
                    <th>数量</th>
                    <th style={{ cursor: 'pointer' }} onClick={() => toggleSort('price')}>
                      成交价{sortBy === 'price' ? (sortDir > 0 ? '↑' : '↓') : ''}
                    </th>
                    <th style={{ cursor: 'pointer' }} onClick={() => toggleSort('amount')}>
                      金额{sortBy === 'amount' ? (sortDir > 0 ? '↑' : '↓') : ''}
                    </th>
                    <th>佣金</th><th>印花税</th>
                    <th style={{ cursor: 'pointer' }} onClick={() => toggleSort('pnl')}>
                      盈亏{sortBy === 'pnl' ? (sortDir > 0 ? '↑' : '↓') : ''}
                    </th>
                    <th style={{ cursor: 'pointer' }} onClick={() => toggleSort('pnl_pct')}>
                      收益率{sortBy === 'pnl_pct' ? (sortDir > 0 ? '↑' : '↓') : ''}
                    </th>
                    <th>持仓天数</th>
                    <th>标签</th>
                  </tr></thead>
                  <tbody>
                    {sortedTrades.map((t, i) => (
                      <tr key={i}>
                        <td style={{ fontSize: 11, whiteSpace: 'nowrap' }}>{t.time?.slice(5)}</td>
                        <td>{t.code}</td><td>{t.name}</td>
                        <td className={t.side === 'buy' ? 'up' : 'down'} style={{ fontWeight: 'bold' }}>{t.side_label}</td>
                        <td><span style={{
                          padding: '2px 6px', borderRadius: 4, fontSize: 11,
                          background: t.side === 'buy' ? 'rgba(239,68,68,0.1)' : 'rgba(34,197,94,0.1)',
                          color: t.side === 'buy' ? 'var(--red)' : 'var(--green)',
                        }}>{t.strategy}</span></td>
                        <td>{t.qty}</td><td>{t.price?.toFixed(2)}</td>
                        <td>{fmt(t.amount)}</td>
                        <td>{t.commission?.toFixed(2)}</td><td>{t.stamp?.toFixed(2)}</td>
                        <td className={t.side === 'sell' ? (t.pnl >= 0 ? 'up' : 'down') : ''} style={{ fontWeight: t.side === 'sell' ? 'bold' : 'normal' }}>
                          {t.side === 'sell' ? (t.pnl >= 0 ? '+' : '') + fmt(t.pnl) : '-'}
                        </td>
                        <td className={t.side === 'sell' ? (t.pnl_pct >= 0 ? 'up' : 'down') : ''}>
                          {t.side === 'sell' ? (t.pnl_pct >= 0 ? '+' : '') + t.pnl_pct + '%' : '-'}
                        </td>
                        <td style={{ fontSize: 12 }}>{t.hold_days != null ? `${t.hold_days}天` : '-'}</td>
                        <td>
                          {t.is_take_profit && <span style={{ color: 'var(--red)', fontSize: 11, fontWeight: 'bold', padding: '1px 4px', borderRadius: 3, background: 'rgba(239,68,68,0.1)' }}>止盈</span>}
                          {t.is_stop_loss && <span style={{ color: 'var(--green)', fontSize: 11, fontWeight: 'bold', padding: '1px 4px', borderRadius: 3, background: 'rgba(34,197,94,0.1)' }}>止损</span>}
                          {!t.is_take_profit && !t.is_stop_loss && t.side === 'sell' && <span style={{ color: 'var(--text3)', fontSize: 11, padding: '1px 4px', borderRadius: 3, background: 'rgba(107,114,128,0.1)' }}>主动卖出</span>}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {/* 盈亏分布图 */}
            {tradeList.filter(t => t.side === 'sell').length > 0 && (
              <div style={{ marginTop: 24 }}>
                <div className="card-title">卖出交易盈亏分布</div>
                <ResponsiveContainer width="100%" height={200}>
                  <BarChart data={tradeList.filter(t => t.side === 'sell').map(t => ({
                    name: `${t.name}(${t.strategy})`,
                    pnl: t.pnl,
                    fill: t.pnl >= 0 ? '#ef4444' : '#22c55e',
                  }))}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                    <XAxis dataKey="name" tick={{ fill: '#9ca3af', fontSize: 10 }} />
                    <YAxis tick={{ fill: '#9ca3af', fontSize: 11 }} />
                    <Tooltip contentStyle={{ background: '#1f2937', border: '1px solid #374151', borderRadius: 8 }}
                      formatter={v => fmt(v)} />
                    <Bar dataKey="pnl" radius={[4, 4, 0, 0]}>
                      {tradeList.filter(t => t.side === 'sell').map((_, i) => <Cell key={i} fill={_.pnl >= 0 ? '#ef4444' : '#22c55e'} />)}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}
          </div>
        </>
      )}

      {/* 曲线图 */}
      {tab === 'chart' && chartData && (
        <>
          {/* 概要卡片 */}
          <div className="card-grid" style={{ marginBottom: 16 }}>
            <Stat label="初始资金" value="100万" />
            <Stat label="当前资产" value={`${(chartData.summary?.current / 10000).toFixed(2)}万`}
              color={chartData.summary?.current >= chartData.summary?.initial ? 'var(--red)' : 'var(--green)'} />
            <Stat label="最高净值" value={`${(chartData.summary?.peak / 10000).toFixed(2)}万`} />
            <Stat label="最大回撤" value={`${chartData.summary?.max_dd}%`} color="var(--red)" />
            <Stat label="交易天数" value={chartData.summary?.trading_days} />
          </div>

          {/* 净值曲线 */}
          <div className="card" style={{ marginBottom: 16 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
              <div className="card-title" style={{ margin: 0 }}>总资产净值曲线</div>
              <span style={{ fontSize: 11, color: 'var(--text3)' }}>拖动下方滑块缩放 | 红线=买入事件 | 蓝线=卖出事件</span>
            </div>
            <ResponsiveContainer width="100%" height={320}>
              <AreaChart data={eqWithEvents}>
                <defs>
                  <linearGradient id="eqGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#3b82f6" stopOpacity={0.3} />
                    <stop offset="100%" stopColor="#3b82f6" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                <XAxis dataKey="date" tick={{ fill: '#6b7280', fontSize: 10 }} tickFormatter={d => d.slice(5)} />
                <YAxis tick={{ fill: '#6b7280', fontSize: 10 }} tickFormatter={v => `${(v / 10000).toFixed(0)}万`}
                  domain={['auto', 'auto']} />
                <Tooltip contentStyle={{ background: '#1f2937', border: '1px solid #374151', borderRadius: 8 }}
                  labelStyle={{ color: '#9ca3af' }} formatter={v => fmt(v)} />
                <Area type="monotone" dataKey="value" stroke="#3b82f6" fill="url(#eqGrad)" strokeWidth={2} name="总资产" />
                {/* 初始资金参考线 */}
                <ReferenceLine y={chartData?.summary?.initial || 1000000} stroke="#6b7280" strokeDasharray="5 5" label={{ value: '初始资金', fill: '#6b7280', fontSize: 10 }} />
                {/* 事件标记线 */}
                {eqWithEvents.filter(pt => pt.events?.length > 0).map((pt, i) => (
                  <ReferenceLine key={i} x={pt.date}
                    stroke={pt.events.some(e => e.type === 'buy') ? '#ef4444' : '#3b82f6'}
                    strokeDasharray="3 3" strokeWidth={1.5} />
                ))}
                {/* 缩放滑块 */}
                <Brush dataKey="date" height={25} stroke="#3b82f6" fill="#111827" tickFormatter={d => d?.slice(5) || ''}>
                  <AreaChart data={eqWithEvents}>
                    <Area type="monotone" dataKey="value" stroke="#3b82f6" fill="#3b82f633" />
                  </AreaChart>
                </Brush>
              </AreaChart>
            </ResponsiveContainer>
          </div>

          <div className="grid-2">
            {/* 回撤曲线 */}
            <div className="card">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                <div className="card-title" style={{ margin: 0 }}>回撤曲线</div>
                <span style={{ fontSize: 11, color: 'var(--text3)' }}>拖动滑块缩放 | 黄线=-5%警戒</span>
              </div>
              <ResponsiveContainer width="100%" height={250}>
                <AreaChart data={chartData.drawdown_curve || []}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                  <XAxis dataKey="date" tick={{ fill: '#6b7280', fontSize: 10 }} tickFormatter={d => d.slice(5)} />
                  <YAxis tick={{ fill: '#6b7280', fontSize: 10 }} tickFormatter={v => `${v}%`}
                    domain={['auto', 0]} />
                  <Tooltip contentStyle={{ background: '#1f2937', border: '1px solid #374151', borderRadius: 8 }}
                    formatter={v => `${v}%`} />
                  {/* -5% 警戒线 */}
                  <ReferenceLine y={-5} stroke="#eab308" strokeDasharray="5 5"
                    label={{ value: '-5% 警戒', fill: '#eab308', fontSize: 10, position: 'left' }} />
                  <ReferenceLine y={-10} stroke="#ef4444" strokeDasharray="5 5"
                    label={{ value: '-10% 危险', fill: '#ef4444', fontSize: 10, position: 'left' }} />
                  <Area type="monotone" dataKey="dd" stroke="#ef4444" fill="#ef444433" strokeWidth={1.5} name="回撤" />
                  <Brush dataKey="date" height={20} stroke="#ef4444" fill="#111827" tickFormatter={d => d?.slice(5) || ''} />
                </AreaChart>
              </ResponsiveContainer>
            </div>

            {/* 策略收益贡献 */}
            <div className="card">
              <div className="card-title">策略收益贡献</div>
              {chartData.strategy_pnl?.length > 0 ? (
                <ResponsiveContainer width="100%" height={220}>
                  <BarChart data={chartData.strategy_pnl}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                    <XAxis dataKey="name" tick={{ fill: '#9ca3af', fontSize: 11 }} />
                    <YAxis tick={{ fill: '#9ca3af', fontSize: 11 }} />
                    <Tooltip contentStyle={{ background: '#1f2937', border: '1px solid #374151', borderRadius: 8 }}
                      formatter={v => fmt(v)} />
                    <Bar dataKey="pnl" name="盈亏" radius={[4, 4, 0, 0]}>
                      {chartData.strategy_pnl.map((entry, i) => (
                        <Cell key={i} fill={entry.pnl >= 0 ? '#ef4444' : '#22c55e'} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              ) : <p style={{ color: 'var(--text3)', textAlign: 'center', padding: 60 }}>卖出交易后显示策略贡献</p>}
            </div>
          </div>

          {/* 每日收益率 */}
          {chartData.daily_returns?.length > 0 && (
            <div className="card" style={{ marginTop: 16 }}>
              <div className="card-title">每日收益率分布</div>
              <ResponsiveContainer width="100%" height={180}>
                <BarChart data={chartData.daily_returns}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                  <XAxis dataKey="date" tick={{ fill: '#6b7280', fontSize: 9 }} tickFormatter={d => d.slice(5)} />
                  <YAxis tick={{ fill: '#9ca3af', fontSize: 10 }} tickFormatter={v => `${v}%`} />
                  <Tooltip contentStyle={{ background: '#1f2937', border: '1px solid #374151', borderRadius: 8 }}
                    formatter={v => `${v}%`} />
                  <Bar dataKey="return" name="日收益率" radius={[2, 2, 0, 0]}>
                    {chartData.daily_returns.map((entry, i) => (
                      <Cell key={i} fill={entry.return >= 0 ? '#ef4444' : '#22c55e'} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
        </>
      )}

      {/* 持仓分析 */}
      {tab === 'positions' && (
        <div className="card">
          <div className="card-title">当前持仓（{d.max_position}只）</div>
          {d.positions?.length === 0 ? (
            <p style={{ color: 'var(--text3)', textAlign: 'center', padding: 40 }}>无持仓</p>
          ) : (
            <table>
              <thead><tr>
                <th>代码</th><th>名称</th><th>持仓</th><th>成本</th><th>现价</th>
                <th>市值</th><th>盈亏</th><th>盈亏%</th><th>权重</th>
              </tr></thead>
              <tbody>
                {d.positions.map(p => (
                  <tr key={p.code}>
                    <td>{p.code}</td><td>{p.name}</td><td>{p.shares}股</td>
                    <td>{p.avg_cost?.toFixed(2)}</td><td>{p.current_price?.toFixed(2)}</td>
                    <td>{fmt(p.market_value)}</td>
                    <td className={p.unrealized_pnl >= 0 ? 'up' : 'down'}>{fmt(p.unrealized_pnl)}</td>
                    <td className={p.unrealized_pnl_pct >= 0 ? 'up' : 'down'}>{p.unrealized_pnl_pct >= 0 ? '+' : ''}{p.unrealized_pnl_pct?.toFixed(2)}%</td>
                    <td>{p.weight_pct}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}

          {d.positions?.length > 0 && (
            <div style={{ marginTop: 24 }}>
              <div className="card-title">仓位分布</div>
              <ResponsiveContainer width="100%" height={200}>
                <BarChart data={[...d.positions, { name: '现金', market_value: d.cash }]}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                  <XAxis dataKey="name" tick={{ fill: '#9ca3af', fontSize: 11 }} />
                  <YAxis tick={{ fill: '#9ca3af', fontSize: 11 }} tickFormatter={v => `${(v / 10000).toFixed(0)}万`} />
                  <Tooltip contentStyle={{ background: '#1f2937', border: '1px solid #374151', borderRadius: 8 }}
                    formatter={v => fmt(v)} />
                  <Bar dataKey="market_value" name="市值" fill="#3b82f6" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function Stat({ label, value, color, sub }) {
  return (
    <div className="stat-card">
      <div className="stat-label">{label}</div>
      <div className="stat-value" style={{ color: color || 'var(--text)', fontSize: 18 }}>{value}</div>
      {sub && <div style={{ fontSize: 11, color: 'var(--text3)', marginTop: 2 }}>{sub}</div>}
    </div>
  )
}

function Metric({ label, value, color }) {
  return (
    <div className="stat-card" style={{ textAlign: 'center' }}>
      <div className="stat-label">{label}</div>
      <div className="stat-value" style={{ color: color || 'var(--text)', fontSize: 16 }}>{value}</div>
    </div>
  )
}
