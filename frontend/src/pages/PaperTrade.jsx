import { useState, useEffect, useCallback } from 'react'
import { fmt } from '../hooks/useApi'

export default function PaperTrade() {
  const [account, setAccount] = useState(null)
  const [positions, setPositions] = useState([])
  const [orders, setOrders] = useState([])
  const [stats, setStats] = useState(null)
  const [tab, setTab] = useState('positions')
  const [form, setForm] = useState({ code: '', side: 'buy', quantity: 100, price: '' })
  const [stockInfo, setStockInfo] = useState(null)
  const [msg, setMsg] = useState('')
  const [msgColor, setMsgColor] = useState('var(--text2)')
  const [loading, setLoading] = useState(false)

  const load = useCallback(async () => {
    const [a, p, o, s] = await Promise.all([
      fetch('/api/paper/account').then(r => r.json()),
      fetch('/api/paper/positions').then(r => r.json()),
      fetch('/api/paper/orders?limit=100').then(r => r.json()),
      fetch('/api/paper/stats').then(r => r.json()),
    ])
    setAccount(a.data || {})
    setPositions(p.data || [])
    setOrders(o.data || [])
    setStats(s.data || {})
  }, [])

  useEffect(() => { load() }, [load])
  useEffect(() => { const t = setInterval(load, 30000); return () => clearInterval(t) }, [load])

  // 查询股票实时价格
  const lookupStock = async (code) => {
    if (!code || code.length < 6) { setStockInfo(null); return }
    try {
      const res = await fetch(`/api/market/stock/${code}`)
      const d = await res.json()
      if (d.code === 0) setStockInfo(d.data)
      else setStockInfo(null)
    } catch { setStockInfo(null) }
  }

  // 下单
  const submit = async () => {
    if (!form.code || form.quantity <= 0) return
    setLoading(true); setMsg('')
    try {
      const body = { code: form.code, side: form.side, quantity: form.quantity }
      if (form.price) body.price = parseFloat(form.price)
      const res = await fetch('/api/paper/order', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
      const d = await res.json()
      if (d.code === 0) {
        setMsg(d.msg); setMsgColor('var(--green2)')
        setForm({ ...form, price: '' })
      } else {
        setMsg(d.msg); setMsgColor('var(--red)')
      }
      load()
    } catch (e) { setMsg('下单失败: ' + e.message); setMsgColor('var(--red)') }
    finally { setLoading(false) }
  }

  if (!account) return <div className="loading">加载模拟账户...</div>

  const equity = account.total_equity || 0
  const retPct = account.total_return_pct || 0
  const isUp = retPct >= 0

  return (
    <div>
      <h2 className="page-title">模拟实盘</h2>

      {/* 账户卡片 */}
      <div className="card-grid" style={{ marginBottom: 16 }}>
        <div className="stat-card">
          <div className="stat-label">总资产</div>
          <div className="stat-value">{(equity / 10000).toFixed(2)}万</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">可用资金</div>
          <div className="stat-value">{(account.cash / 10000).toFixed(2)}万</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">持仓市值</div>
          <div className="stat-value">{((account.total_market_value || 0) / 10000).toFixed(2)}万</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">累计盈亏</div>
          <div className="stat-value" style={{ color: isUp ? 'var(--red)' : 'var(--green)' }}>
            {retPct >= 0 ? '+' : ''}{retPct.toFixed(2)}%
          </div>
          <div className="stat-change" style={{ color: isUp ? 'var(--red)' : 'var(--green)', fontSize: 12 }}>
            {((account.total_unrealized_pnl || 0) + (account.total_realized_pnl || 0)) >= 0 ? '+' : ''}
            {(((account.total_unrealized_pnl || 0) + (account.total_realized_pnl || 0)) / 10000).toFixed(2)}万
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-label">浮动盈亏</div>
          <div className="stat-value" style={{ color: (account.total_unrealized_pnl || 0) >= 0 ? 'var(--red)' : 'var(--green)' }}>
            {((account.total_unrealized_pnl || 0) >= 0 ? '+' : '')}{((account.total_unrealized_pnl || 0) / 10000).toFixed(2)}万
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-label">已实现盈亏</div>
          <div className="stat-value" style={{ color: (account.total_realized_pnl || 0) >= 0 ? 'var(--red)' : 'var(--green)' }}>
            {((account.total_realized_pnl || 0) >= 0 ? '+' : '')}{((account.total_realized_pnl || 0) / 10000).toFixed(2)}万
          </div>
        </div>
      </div>

      <div style={{ display: 'flex', gap: 8, marginBottom: 16, alignItems: 'center' }}>
        <button className="btn btn-sm" onClick={load}>刷新</button>
        <span style={{ color: 'var(--text3)', fontSize: 12, marginLeft: 'auto' }}>
          {positions.length}个持仓 | 佣金万2.5 | 印花税0.1%(卖) | T+1 | 100股整数倍
        </span>
      </div>

      {/* Tab */}
      <div className="tab-bar">
        {['positions', 'trade', 'orders', 'stats'].map(t => (
          <button key={t} className={`tab-btn ${tab === t ? 'active' : ''}`} onClick={() => setTab(t)}>
            {{ positions: '持仓', trade: '交易', orders: '流水', stats: '统计' }[t]}
          </button>
        ))}
      </div>

      {/* 持仓列表 */}
      {tab === 'positions' && (
        positions.length === 0 ? (
          <div className="card" style={{ textAlign: 'center', padding: 40 }}>
            <p style={{ color: 'var(--text3)' }}>暂无持仓，点击「交易」买入</p>
          </div>
        ) : (
          <table>
            <thead><tr>
              <th>代码</th><th>名称</th><th>持仓</th><th>成本价</th><th>现价</th>
              <th>市值</th><th>盈亏</th><th>盈亏%</th><th>权重</th>
            </tr></thead>
            <tbody>
              {positions.map(p => (
                <tr key={p.code}>
                  <td>{p.code}</td>
                  <td><span className="link" onClick={() => { setForm({ ...form, code: p.code, side: 'sell' }); setTab('trade'); lookupStock(p.code) }}>{p.name}</span></td>
                  <td>{p.shares}</td>
                  <td>{p.avg_cost?.toFixed(3)}</td>
                  <td>{p.current_price?.toFixed(2)}</td>
                  <td>{fmt(p.market_value)}</td>
                  <td className={p.unrealized_pnl >= 0 ? 'up' : 'down'}>{fmt(p.unrealized_pnl)}</td>
                  <td className={p.unrealized_pnl_pct >= 0 ? 'up' : 'down'}>{p.unrealized_pnl_pct >= 0 ? '+' : ''}{p.unrealized_pnl_pct?.toFixed(2)}%</td>
                  <td>{p.weight_pct?.toFixed(1)}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        )
      )}

      {/* 交易面板 */}
      {tab === 'trade' && (
        <div style={{ display: 'flex', gap: 20 }}>
          <div className="card" style={{ flex: 1, maxWidth: 450 }}>
            <div className="card-title">下单</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              <div style={{ display: 'flex', gap: 8 }}>
                <input value={form.code} onChange={e => { setForm({ ...form, code: e.target.value }); lookupStock(e.target.value) }}
                  placeholder="股票代码 例:600519" style={inpStyle} />
                <button className="btn btn-sm" onClick={() => lookupStock(form.code)}>查</button>
              </div>

              <div style={{ display: 'flex', gap: 8 }}>
                <button className={`btn ${form.side === 'buy' ? 'btn-primary' : ''}`}
                  onClick={() => setForm({ ...form, side: 'buy' })}
                  style={{ flex: 1, padding: '10px 0', fontSize: 16, color: form.side === 'buy' ? 'white' : 'var(--red)' }}>
                  买入
                </button>
                <button className={`btn ${form.side === 'sell' ? 'btn-primary' : ''}`}
                  onClick={() => setForm({ ...form, side: 'sell' })}
                  style={{ flex: 1, padding: '10px 0', fontSize: 16, color: form.side === 'sell' ? 'white' : 'var(--green)' }}>
                  卖出
                </button>
              </div>

              {/* 实时行情 */}
              {stockInfo && (
                <div style={{ background: 'var(--bg)', borderRadius: 6, padding: 12, border: '1px solid var(--border)' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                    <span style={{ fontWeight: 'bold' }}>{stockInfo.name}</span>
                    <span className={stockInfo.change_pct >= 0 ? 'up' : 'down'} style={{ fontWeight: 'bold', fontSize: 18 }}>
                      {stockInfo.price?.toFixed(2)}
                    </span>
                  </div>
                  <div style={{ display: 'flex', gap: 16, fontSize: 12, color: 'var(--text3)' }}>
                    <span>涨跌: <span className={stockInfo.change_pct >= 0 ? 'up' : 'down'}>{stockInfo.change_pct >= 0 ? '+' : ''}{stockInfo.change_pct?.toFixed(2)}%</span></span>
                    <span>最高: {stockInfo.high?.toFixed(2)}</span>
                    <span>最低: {stockInfo.low?.toFixed(2)}</span>
                  </div>
                </div>
              )}

              {/* 数量 */}
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <label style={{ fontSize: 12, color: 'var(--text2)' }}>数量</label>
                  <div style={{ display: 'flex', gap: 4 }}>
                    {[100, 200, 500, 1000, 2000, 5000].map(n => (
                      <button key={n} className="btn btn-sm" style={{ padding: '2px 8px', fontSize: 11 }}
                        onClick={() => setForm({ ...form, quantity: n })}>{n >= 1000 ? `${n / 1000}k` : n}</button>
                    ))}
                  </div>
                </div>
                <input type="number" value={form.quantity}
                  onChange={e => setForm({ ...form, quantity: parseInt(e.target.value) || 0 })}
                  style={inpStyle} />
              </div>

              {/* 限价 */}
              <div>
                <label style={{ fontSize: 12, color: 'var(--text2)' }}>限价（留空=市价）</label>
                <input type="number" step="0.01" value={form.price}
                  onChange={e => setForm({ ...form, price: e.target.value })}
                  placeholder={stockInfo ? `当前价 ${stockInfo.price?.toFixed(2)}` : '输入价格'}
                  style={inpStyle} />
              </div>

              {/* 预估 */}
              {stockInfo && form.quantity > 0 && (
                <div style={{ background: 'var(--bg)', borderRadius: 6, padding: 8, fontSize: 12, color: 'var(--text3)' }}>
                  预估金额: {(form.quantity * (parseFloat(form.price) || stockInfo.price || 0)).toFixed(2)}元
                  {form.side === 'buy' && ` + 佣金${(form.quantity * (parseFloat(form.price) || stockInfo.price) * 0.00025).toFixed(2)}`}
                  {form.side === 'sell' && ` - 佣金${(form.quantity * (parseFloat(form.price) || stockInfo.price) * 0.00025).toFixed(2)} - 印花税${(form.quantity * (parseFloat(form.price) || stockInfo.price) * 0.001).toFixed(2)}`}
                </div>
              )}

              {/* 提交 */}
              <button className="btn btn-primary" onClick={submit} disabled={loading || !form.code || form.quantity <= 0}
                style={{ padding: '12px 0', fontSize: 18, background: form.side === 'buy' ? 'var(--red)' : 'var(--green)', borderColor: 'transparent' }}>
                {loading ? '处理中...' : `${form.side === 'buy' ? '买入' : '卖出'} ${form.code || ''}`}
              </button>

              {msg && <div style={{ textAlign: 'center', fontSize: 13, color: msgColor }}>{msg}</div>}
            </div>
          </div>

          {/* 快捷卖出（显示当前持仓） */}
          <div style={{ flex: 1 }}>
            <div className="card-title" style={{ marginBottom: 12 }}>当前持仓（点击快速卖出）</div>
            {positions.length === 0 ? (
              <p style={{ color: 'var(--text3)', fontSize: 13 }}>暂无持仓</p>
            ) : positions.map(p => (
              <div key={p.code} className="stat-card" style={{ marginBottom: 8, cursor: 'pointer',
                border: form.code === p.code && form.side === 'sell' ? '1px solid var(--green)' : '1px solid transparent' }}
                onClick={() => { setForm({ code: p.code, side: 'sell', quantity: p.shares, price: '' }); lookupStock(p.code) }}>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ fontWeight: 'bold' }}>{p.name} ({p.code})</span>
                  <span className={p.unrealized_pnl_pct >= 0 ? 'up' : 'down'}>
                    {p.unrealized_pnl_pct >= 0 ? '+' : ''}{p.unrealized_pnl_pct?.toFixed(2)}%
                  </span>
                </div>
                <div style={{ fontSize: 12, color: 'var(--text3)', marginTop: 4 }}>
                  {p.shares}股 | 成本{p.avg_cost?.toFixed(2)} | 现价{p.current_price?.toFixed(2)} | 盈亏{fmt(p.unrealized_pnl)}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 交易流水 */}
      {tab === 'orders' && (
        orders.length === 0 ? (
          <div className="card" style={{ textAlign: 'center', padding: 40 }}>
            <p style={{ color: 'var(--text3)' }}>暂无交易记录</p>
          </div>
        ) : (
          <table>
            <thead><tr>
              <th>时间</th><th>代码</th><th>名称</th><th>方向</th><th>数量</th><th>成交价</th><th>手续费</th><th>盈亏</th>
            </tr></thead>
            <tbody>
              {orders.map(o => (
                <tr key={o.id}>
                  <td style={{ fontSize: 11, whiteSpace: 'nowrap' }}>{o.time?.slice(5)}</td>
                  <td>{o.code}</td><td>{o.name}</td>
                  <td className={o.side === 'buy' ? 'up' : 'down'}>{o.side === 'buy' ? '买入' : '卖出'}</td>
                  <td>{o.qty}</td>
                  <td>{o.price?.toFixed(2)}</td>
                  <td>{o.fee?.toFixed(2)}</td>
                  <td className={o.side === 'sell' ? (o.pnl >= 0 ? 'up' : 'down') : ''}>{o.side === 'sell' ? (o.pnl >= 0 ? '+' : '') + o.pnl?.toFixed(2) : '-'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )
      )}

      {/* 统计 */}
      {tab === 'stats' && stats && (
        <div className="card">
          <div className="card-title">交易统计</div>
          <div className="card-grid" style={{ marginBottom: 16 }}>
            <StatCard label="总成交" value={stats.total_trades || 0} />
            <StatCard label="买入" value={stats.buy_trades || 0} />
            <StatCard label="卖出" value={stats.sell_trades || 0} />
            <StatCard label="胜率" value={stats.sell_trades > 0 ? `${((stats.win_trades || 0) / ((stats.win_trades || 0) + (stats.loss_trades || 0)) * 100).toFixed(0)}%` : '-'} />
            <StatCard label="盈亏比" value={stats.avg_loss ? (Math.abs(stats.avg_win / stats.avg_loss)).toFixed(1) : '-'} />
            <StatCard label="总佣金" value={`${(stats.total_commission || 0).toFixed(2)}`} />
            <StatCard label="已实现盈亏" value={fmt(stats.total_realized_pnl)} color={(stats.total_realized_pnl || 0) >= 0 ? 'var(--red)' : 'var(--green)'} />
          </div>
        </div>
      )}
    </div>
  )
}

const inpStyle = {
  width: '100%', padding: '10px 12px', background: 'var(--bg3)', border: '1px solid var(--border)',
  borderRadius: 6, color: 'var(--text)', fontSize: 14, marginTop: 4,
}

function StatCard({ label, value, color }) {
  return (
    <div className="stat-card">
      <div className="stat-label">{label}</div>
      <div className="stat-value" style={{ color, fontSize: 18 }}>{value}</div>
    </div>
  )
}
