import { useState, useEffect, useCallback } from 'react'
import { fmt } from '../hooks/useApi'

export default function AutoTrade() {
  const [status, setStatus] = useState(null)
  const [logs, setLogs] = useState([])
  const [account, setAccount] = useState(null)
  const [positions, setPositions] = useState([])
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [config, setConfig] = useState({ strategy: 'breakout', tp: 20, sl: -8, interval: 60, t0_mode: false })
  const [tpSlStatus, setTpSlStatus] = useState(null)
  const [wxConfig, setWxConfig] = useState(null)

  const load = useCallback(async () => {
    const [s, l, a, p, tp, wx] = await Promise.all([
      fetch('/api/autotrade/status').then(r => r.json()),
      fetch('/api/autotrade/logs?limit=50').then(r => r.json()),
      fetch('/api/paper/account').then(r => r.json()),
      fetch('/api/paper/positions').then(r => r.json()),
      fetch('/api/tp-sl/status').then(r => r.json()),
      fetch('/api/wx/config').then(r => r.json()),
    ])
    setStatus(s.data || {})
    setLogs(l.data || [])
    setAccount(a.data || {})
    setPositions(p.data || [])
    setTpSlStatus(tp.data || {})
    setWxConfig(wx.data || {})
    if (s.data?.strategy) setConfig(c => ({
      ...c,
      strategy: s.data.strategy,
      tp: s.data.tp_pct || 20,
      sl: s.data.sl_pct || -8,
      interval: s.data.interval || 60,
      t0_mode: s.data.t0_mode || false,
    }))
  }, [])

  useEffect(() => { load() }, [load])
  useEffect(() => { const t = setInterval(load, 30000); return () => clearInterval(t) }, [load])

  const toggle = async (enabled) => {
    await fetch('/api/autotrade/toggle', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ enabled })
    })
    load()
  }

  const runOnce = async () => {
    setLoading(true); setResult(null)
    try {
      const res = await fetch('/api/autotrade/run')
      const d = await res.json()
      setResult(d)
      load()
    } catch { }
    finally { setLoading(false) }
  }

  const updateConfig = async () => {
    await fetch('/api/autotrade/config', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(config)
    })
    load()
  }

  const toggleTpSl = async (enabled) => {
    await fetch('/api/tp-sl/toggle', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ enabled })
    })
    load()
  }

  const toggleT0 = async () => {
    await fetch('/api/autotrade/config', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ t0_mode: !config.t0_mode })
    })
    load()
  }

  const testWx = async () => {
    try {
      await fetch('/api/wx/test')
      alert('推送已发送，请检查企业微信')
    } catch { alert('推送失败') }
  }

  const logColor = { INFO: 'var(--text2)', WARN: 'var(--yellow)', ALERT: 'var(--red)' }
  const strategyNames = { breakout: '放量突破', bluechip: '低估值蓝筹', limitup: '涨停板', active: '高换手活跃' }
  const isOn = status?.enabled
  const tpSlOn = tpSlStatus?.enabled

  return (
    <div>
      <h2 className="page-title">自动交易</h2>

      {/* 状态卡片 */}
      <div className="card-grid" style={{ marginBottom: 16 }}>
        <div className="stat-card">
          <div className="stat-label">状态</div>
          <div className="stat-value" style={{ fontSize: 18, color: isOn ? 'var(--green2)' : 'var(--text3)' }}>
            {isOn ? '运行中' : '已停止'}
          </div>
          {status?.last_run && <div style={{ fontSize: 11, color: 'var(--text3)' }}>上次: {status.last_run}</div>}
        </div>
        <div className="stat-card">
          <div className="stat-label">策略</div>
          <div className="stat-value" style={{ fontSize: 16 }}>{strategyNames[config.strategy] || config.strategy}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">止盈/止损</div>
          <div className="stat-value" style={{ fontSize: 16 }}>
            <span style={{ color: 'var(--red)' }}>+{config.tp}%</span> / <span style={{ color: 'var(--green)' }}>{config.sl}%</span>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-label">今日交易</div>
          <div className="stat-value" style={{ fontSize: 18 }}>{status?.trade_count_today || 0} / {status?.max_daily_trades || 10}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">总资产</div>
          <div className="stat-value" style={{ fontSize: 18 }}>{account ? (account.total_equity / 10000).toFixed(2) + '万' : '-'}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">持仓数</div>
          <div className="stat-value" style={{ fontSize: 18 }}>{positions.length} / {status?.max_positions || 8}</div>
        </div>
      </div>

      {/* 监控状态 */}
      <div className="card-grid" style={{ marginBottom: 16 }}>
        <div className="stat-card">
          <div className="stat-label">止盈止损监控</div>
          <div className="stat-value" style={{ fontSize: 16, color: tpSlOn ? 'var(--green2)' : 'var(--text3)' }}>
            {tpSlOn ? '运行中' : '已停止'}
          </div>
          {tpSlStatus?.last_check && <div style={{ fontSize: 11, color: 'var(--text3)' }}>上次检查: {tpSlStatus.last_check}</div>}
        </div>
        <div className="stat-card">
          <div className="stat-label">T+0模式</div>
          <div className="stat-value" style={{ fontSize: 16, color: config.t0_mode ? 'var(--green2)' : 'var(--text3)' }}>
            {config.t0_mode ? '已开启' : '已关闭'}
          </div>
          <div style={{ fontSize: 11, color: 'var(--text3)' }}>{config.t0_mode ? '当日可买卖' : 'T+1限制'}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">企业微信推送</div>
          <div className="stat-value" style={{ fontSize: 16, color: wxConfig?.enabled ? 'var(--green2)' : 'var(--red)' }}>
            {wxConfig?.enabled ? '已配置' : '未配置'}
          </div>
        </div>
      </div>

      {/* 控制 + 配置 */}
      <div className="card" style={{ marginBottom: 16 }}>
        <div style={{ display: 'flex', gap: 16, alignItems: 'center', flexWrap: 'wrap' }}>
          {/* 策略选择 */}
          <div>
            <label style={{ fontSize: 12, color: 'var(--text3)' }}>策略</label>
            <select value={config.strategy} onChange={e => setConfig({ ...config, strategy: e.target.value })}
              style={selStyle}>
              <option value="breakout">放量突破</option>
              <option value="bluechip">低估值蓝筹</option>
              <option value="limitup">涨停板</option>
              <option value="active">高换手活跃</option>
            </select>
          </div>
          {/* 止盈 */}
          <div>
            <label style={{ fontSize: 12, color: 'var(--text3)' }}>止盈%</label>
            <input type="number" value={config.tp} onChange={e => setConfig({ ...config, tp: parseFloat(e.target.value) || 20 })}
              style={{ ...inpStyle, width: 70 }} />
          </div>
          {/* 止损 */}
          <div>
            <label style={{ fontSize: 12, color: 'var(--text3)' }}>止损%</label>
            <input type="number" value={config.sl} onChange={e => setConfig({ ...config, sl: parseFloat(e.target.value) || -8 })}
              style={{ ...inpStyle, width: 70 }} />
          </div>
          {/* 间隔 */}
          <div>
            <label style={{ fontSize: 12, color: 'var(--text3)' }}>间隔(秒)</label>
            <input type="number" value={config.interval} onChange={e => setConfig({ ...config, interval: parseInt(e.target.value) || 60 })}
              style={{ ...inpStyle, width: 70 }} />
          </div>
          {/* T+0开关 */}
          <div>
            <label style={{ fontSize: 12, color: 'var(--text3)' }}>T+0模式</label>
            <button onClick={toggleT0}
              style={{
                ...selStyle,
                background: config.t0_mode ? 'var(--green2)' : 'var(--bg3)',
                color: config.t0_mode ? '#fff' : 'var(--text3)',
                minWidth: 60,
              }}>
              {config.t0_mode ? '开启' : '关闭'}
            </button>
          </div>

          <div style={{ marginLeft: 'auto', display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            <button className="btn btn-sm" onClick={updateConfig}>更新配置</button>
            {isOn ? (
              <button className="btn" onClick={() => toggle(false)} style={{ color: 'var(--red)', borderColor: 'var(--red)' }}>停止</button>
            ) : (
              <button className="btn btn-primary" onClick={() => toggle(true)}>开启自动交易</button>
            )}
            <button className="btn btn-sm" onClick={runOnce} disabled={loading}>{loading ? '执行中...' : '手动执行一次'}</button>
          </div>
        </div>
        <div style={{ display: 'flex', gap: 16, marginTop: 12, alignItems: 'center', borderTop: '1px solid var(--border)', paddingTop: 12 }}>
          <div style={{ fontSize: 12, color: 'var(--text3)' }}>止盈止损监控:</div>
          {tpSlOn ? (
            <button className="btn btn-sm" onClick={() => toggleTpSl(false)} style={{ color: 'var(--red)', borderColor: 'var(--red)', fontSize: 11 }}>停止监控</button>
          ) : (
            <button className="btn btn-sm btn-primary" onClick={() => toggleTpSl(true)} style={{ fontSize: 11 }}>启动监控</button>
          )}
          <div style={{ marginLeft: 'auto' }}>
            <button className="btn btn-sm" onClick={testWx} style={{ fontSize: 11 }}>测试企业微信推送</button>
          </div>
        </div>
      </div>

      {/* 执行结果 */}
      {result && (
        <div className="card" style={{ marginBottom: 16 }}>
          <div className="card-title">最近执行结果</div>
          {result.actions?.length === 0 ? (
            <p style={{ color: 'var(--text3)' }}>无操作（无信号或无条件触发）</p>
          ) : (
            <table>
              <thead><tr><th>方向</th><th>股票</th><th>原因</th><th>结果</th></tr></thead>
              <tbody>
                {result.actions?.map((a, i) => (
                  <tr key={i}>
                    <td className={a.action === 'BUY' ? 'up' : 'down'} style={{ fontWeight: 'bold' }}>{a.action}</td>
                    <td>{a.name} ({a.code})</td>
                    <td style={{ fontSize: 12, color: 'var(--text2)' }}>{a.reason}</td>
                    <td style={{ color: a.ok ? 'var(--green2)' : 'var(--red)' }}>{a.ok ? '成功' : '跳过'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          {result.account && (
            <div style={{ marginTop: 8, fontSize: 13, color: 'var(--text3)' }}>
              总资产 {fmt(result.account.total_equity)} | 持仓 {result.account.position_count}只
            </div>
          )}
        </div>
      )}

      <div className="grid-2">
        {/* 持仓盈亏 */}
        <div className="card">
          <div className="card-title">持仓（止盈止损监控）</div>
          {positions.length === 0 ? (
            <p style={{ color: 'var(--text3)', padding: 20 }}>无持仓</p>
          ) : (
            <table>
              <thead><tr><th>股票</th><th>盈亏%</th><th>状态</th></tr></thead>
              <tbody>
                {positions.map(p => {
                  const pnl = p.unrealized_pnl_pct || 0
                  const hitTP = pnl >= config.tp
                  const hitSL = pnl <= config.sl
                  return (
                    <tr key={p.code}>
                      <td><strong>{p.name}</strong><br /><span style={{ fontSize: 11, color: 'var(--text3)' }}>{p.shares}股 @{p.avg_cost?.toFixed(2)} 现{p.current_price?.toFixed(2)}</span></td>
                      <td className={pnl >= 0 ? 'up' : 'down'} style={{ fontWeight: 'bold' }}>{pnl >= 0 ? '+' : ''}{pnl?.toFixed(2)}%</td>
                      <td>
                        {hitTP && <span style={{ color: 'var(--red)', fontWeight: 'bold' }}>止盈</span>}
                        {hitSL && <span style={{ color: 'var(--green)', fontWeight: 'bold' }}>止损</span>}
                        {!hitTP && !hitSL && <span style={{ color: 'var(--text3)', fontSize: 12 }}>持有中</span>}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          )}
        </div>

        {/* 日志 */}
        <div className="card">
          <div className="card-title">交易日志 ({logs.length})</div>
          <div style={{ maxHeight: 400, overflow: 'auto', fontFamily: 'monospace', fontSize: 12 }}>
            {logs.length === 0 ? (
              <p style={{ color: 'var(--text3)', padding: 20 }}>暂无日志</p>
            ) : logs.map((l, i) => (
              <div key={i} style={{ padding: '4px 0', borderBottom: '1px solid var(--border)', display: 'flex', gap: 6 }}>
                <span style={{ color: 'var(--text3)', minWidth: 55, flexShrink: 0 }}>{l.time}</span>
                <span style={{ color: '#6366f1', minWidth: 45, flexShrink: 0 }}>[{l.event}]</span>
                <span style={{ color: logColor[l.level] || 'var(--text2)', flex: 1, wordBreak: 'break-all' }}>{l.msg}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}

const inpStyle = {
  padding: '6px 8px', background: 'var(--bg3)', border: '1px solid var(--border)',
  borderRadius: 6, color: 'var(--text)', fontSize: 13,
}
const selStyle = {
  ...inpStyle, marginTop: 0,
}
