import { useState, useEffect, useCallback, useRef } from 'react'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Cell } from 'recharts'

export default function ModelCenter() {
  const [model, setModel] = useState(null)
  const [logFiles, setLogFiles] = useState([])
  const [tab, setTab] = useState('overview')
  const [loading, setLoading] = useState(false)
  const [logContent, setLogContent] = useState('')
  const [logFile, setLogFile] = useState('')
  const [comparison, setComparison] = useState(null)

  const load = useCallback(async () => {
    try {
      const [m, l] = await Promise.all([
        fetch('/api/model/status').then(r => r.json()),
        fetch('/api/model/logs').then(r => r.json()),
      ])
      setModel(m.data)
      setLogFiles(l.data || [])
    } catch { }
  }, [])

  useEffect(() => { load() }, [load])
  // Auto-refresh during training
  useEffect(() => {
    if (model?.status === 'training') {
      const t = setInterval(load, 30000)
      return () => clearInterval(t)
    }
  }, [model?.status, load])

  const startTrain = async () => {
    setLoading(true)
    await fetch('/api/model/train')
    load()
  }

  const stopTrain = async () => {
    await fetch('/api/model/stop')
    load()
  }

  const switchVersion = async (version) => {
    await fetch(`/api/model/switch?version=${version}`)
    load()
  }

  const viewLog = async (file) => {
    setLogFile(file)
    try {
      const res = await fetch(`/api/model/log-content?file=${encodeURIComponent(file)}`)
      const d = await res.json()
      setLogContent(d.content || d.msg || '')
    } catch { setLogContent('读取失败') }
  }

  const loadComparison = async () => {
    try {
      const res = await fetch('/api/model/compare')
      const d = await res.json()
      setComparison(d.data)
    } catch { }
  }

  if (!model) return <div className="loading">加载模型数据...</div>

  const isTraining = model.status === 'training'
  const statusLabel = { untrained: '未训练', training: '训练中', trained: '已训练' }
  const statusColor = { untrained: 'var(--yellow)', training: 'var(--blue)', trained: 'var(--green2)' }
  const m = model.metrics || {}

  return (
    <div>
      <h2 className="page-title">模型与训练管理</h2>

      {/* 状态卡片 */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(6, 1fr)', gap: 12, marginBottom: 20 }}>
        <StatCard label="模型状态" value={statusLabel[model.status]} color={statusColor[model.status]} />
        <StatCard label="当前版本" value={model.version} />
        <StatCard label="IC均值" value={m.ic_mean} color={m.ic_mean > 0.03 ? 'var(--green2)' : 'var(--text)'} />
        <StatCard label="IR值" value={m.ir} />
        <StatCard label="胜率" value={`${m.win_rate}%`} />
        <StatCard label="Sharpe" value={m.sharpe} color={m.sharpe > 1.5 ? 'var(--green2)' : 'var(--yellow)'} />
      </div>

      {/* 训练控制 */}
      <div className="card" style={{ marginBottom: 16 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
          <div style={{ flex: 1 }}>
            <div style={{ fontWeight: 'bold', marginBottom: 4 }}>
              {isTraining ? '训练进度' : '训练控制'}
            </div>
            {isTraining && (
              <div style={{ marginBottom: 8 }}>
                <div style={{
                  width: '100%', height: 8, background: 'var(--bg3)', borderRadius: 4, overflow: 'hidden',
                }}>
                  <div style={{
                    width: `${model.train_progress}%`, height: '100%',
                    background: 'var(--blue)', borderRadius: 4,
                    transition: 'width 0.5s ease',
                  }} />
                </div>
                <div style={{ fontSize: 12, color: 'var(--text3)', marginTop: 4 }}>
                  {model.train_progress}%
                </div>
              </div>
            )}
            {model.last_train && (
              <div style={{ fontSize: 12, color: 'var(--text3)' }}>
                上次训练: {model.last_train}
              </div>
            )}
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            {isTraining ? (
              <button className="btn" onClick={stopTrain} style={{ color: 'var(--red)' }}>停止训练</button>
            ) : (
              <button className="btn btn-primary" onClick={startTrain} disabled={loading}>
                {loading ? '启动中...' : '手动触发训练'}
              </button>
            )}
          </div>
        </div>

        {/* 实时训练日志 */}
        {isTraining && model.train_log && (
          <div style={{
            marginTop: 16, background: 'var(--bg)', borderRadius: 6, padding: 12,
            maxHeight: 200, overflow: 'auto', fontFamily: 'monospace', fontSize: 12,
          }}>
            {model.train_log.split('\n').map((line, i) => (
              <div key={i} style={{
                color: line.includes('完成') ? 'var(--green2)' : line.includes('...') ? 'var(--text)' : 'var(--text3)',
                padding: '2px 0',
              }}>
                {line}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Tab */}
      <div className="tab-bar" style={{ marginBottom: 16 }}>
        {['overview', 'versions', 'logs'].map(t => (
          <button key={t} className={`tab-btn ${tab === t ? 'active' : ''}`} onClick={() => setTab(t)}>
            {{ overview: '指标概览', versions: '版本历史', logs: '训练日志' }[t]}
          </button>
        ))}
      </div>

      {/* 指标概览 */}
      {tab === 'overview' && (
        <div className="grid-2">
          <div className="card">
            <div className="card-title">模型核心指标</div>
            <div className="card-grid" style={{ gridTemplateColumns: '1fr 1fr' }}>
              <MetricCard label="IC均值" value={m.ic_mean} color={m.ic_mean > 0.03 ? 'var(--green2)' : 'var(--text)'} />
              <MetricCard label="IR值" value={m.ir} />
              <MetricCard label="胜率" value={`${m.win_rate}%`}
                color={m.win_rate >= 55 ? 'var(--green2)' : m.win_rate > 0 ? 'var(--yellow)' : 'var(--text)'} />
              <MetricCard label="Sharpe" value={m.sharpe}
                color={m.sharpe > 1.5 ? 'var(--green2)' : 'var(--yellow)'} />
              <MetricCard label="回测收益" value={`${m.backtest_return}%`}
                color={m.backtest_return > 0 ? 'var(--red)' : 'var(--green)'} />
              <MetricCard label="最大回撤" value={`${m.max_drawdown}%`} color="var(--red)" />
            </div>
          </div>
          <div className="card">
            <div className="card-title">指标对比</div>
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={[
                { name: 'IC', value: (m.ic_mean || 0) * 100, fill: '#3b82f6' },
                { name: 'IR', value: (m.ir || 0) * 100, fill: '#a855f7' },
                { name: '胜率', value: m.win_rate || 0, fill: '#22c55e' },
                { name: 'Sharpe', value: (m.sharpe || 0) * 20, fill: '#f97316' },
                { name: '收益%', value: Math.max(0, m.backtest_return || 0), fill: '#ef4444' },
              ]}>
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                <XAxis dataKey="name" tick={{ fill: '#9ca3af' }} />
                <YAxis tick={{ fill: '#9ca3af' }} />
                <Tooltip contentStyle={{ background: '#1f2937', border: '1px solid #374151', borderRadius: 8 }} />
                <Bar dataKey="value" radius={[4, 4, 0, 0]}>
                  {[{ fill: '#3b82f6' }, { fill: '#a855f7' }, { fill: '#22c55e' }, { fill: '#f97316' }, { fill: '#ef4444' }].map((e, i) => (
                    <Cell key={i} fill={e.fill} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* 版本历史 */}
      {tab === 'versions' && (
        <div className="card">
          <div className="card-title">模型版本列表</div>
          <table>
            <thead><tr><th>版本</th><th>时间</th><th>状态</th><th>IC</th><th>IR</th><th>Sharpe</th><th>胜率</th><th>收益</th><th>操作</th></tr></thead>
            <tbody>
              {model.versions?.map(v => (
                <tr key={v.version}>
                  <td style={{ fontFamily: 'monospace', fontWeight: 'bold' }}>{v.version}</td>
                  <td style={{ fontSize: 12, color: 'var(--text3)' }}>{v.date}</td>
                  <td>
                    <span style={{
                      padding: '2px 8px', borderRadius: 4, fontSize: 11, fontWeight: 'bold',
                      background: v.status === 'current' ? 'rgba(34,197,94,0.1)' : 'rgba(107,114,128,0.1)',
                      color: v.status === 'current' ? 'var(--green2)' : 'var(--text3)',
                    }}>
                      {v.status === 'current' ? '当前' : '历史'}
                    </span>
                  </td>
                  <td>{v.metrics?.ic?.toFixed(3)}</td>
                  <td>{v.metrics?.ir?.toFixed(2)}</td>
                  <td>{v.metrics?.sharpe?.toFixed(2)}</td>
                  <td>{v.metrics?.win_rate?.toFixed(1)}%</td>
                  <td className={(v.metrics?.return_pct || 0) >= 0 ? 'up' : 'down'}>
                    {v.metrics?.return_pct}%
                  </td>
                  <td>
                    {v.status !== 'current' && (
                      <button className="btn btn-sm" onClick={() => switchVersion(v.version)}>
                        切换
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* 训练日志 */}
      {tab === 'logs' && (
        <div>
          {/* 日志文件列表 */}
          <div className="card" style={{ marginBottom: 16 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
              <div className="card-title" style={{ margin: 0 }}>训练日志文件</div>
              <button className="btn btn-sm" onClick={load}>刷新</button>
            </div>
            {logFiles.length === 0 ? (
              <p style={{ color: 'var(--text3)', textAlign: 'center', padding: 20 }}>暂无日志（训练一次后自动生成）</p>
            ) : (
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                {logFiles.map(f => (
                  <button key={f.name} className={`btn btn-sm ${logFile === f.name ? 'btn-primary' : ''}`}
                    onClick={() => viewLog(f.name)}>
                    {f.name.slice(0, 16)} ({(f.size / 1024).toFixed(1)}KB)
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* 日志内容 */}
          {logContent && (
            <div className="card" style={{ marginBottom: 16 }}>
              <div className="card-title">
                日志内容: {logFile}
              </div>
              <div style={{
                background: 'var(--bg)', borderRadius: 6, padding: 16, maxHeight: 500, overflow: 'auto',
                fontFamily: 'monospace', fontSize: 12,
              }}>
                {logContent.split('\n').map((line, i) => {
                  const isError = line.toLowerCase().includes('error') || line.toLowerCase().includes('失败')
                  const isSuccess = line.includes('完成') || line.includes('Save') || line.includes('--- 结果 ---')
                  const isWarning = line.includes('...')
                  return (
                    <div key={i} style={{
                      color: isError ? 'var(--red)' : isSuccess ? 'var(--green2)' : isWarning ? 'var(--text2)' : 'var(--text3)',
                      padding: '1px 0', fontWeight: isError ? 'bold' : 'normal',
                    }}>
                      {line || ' '}
                    </div>
                  )
                })}
              </div>
            </div>
          )}

          {/* 模型回测对比 */}
          <div className="card">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
              <div className="card-title" style={{ margin: 0 }}>模型 vs 策略回测对比</div>
              <button className="btn btn-sm" onClick={loadComparison}>生成对比</button>
            </div>

            {comparison ? (
              <>
                {/* 对比表 */}
                <table style={{ marginBottom: 16 }}>
                  <thead><tr><th>策略</th><th>Sharpe</th><th>收益%</th><th>回撤%</th><th>评价</th></tr></thead>
                  <tbody>
                    {comparison.comparison?.map((c, i) => (
                      <tr key={i}>
                        <td style={{ fontWeight: c.name?.includes('AI') ? 'bold' : 'normal', color: c.name?.includes('AI') ? 'var(--blue)' : 'var(--text)' }}>
                          {c.name}
                        </td>
                        <td style={{ color: c.sharpe >= 1.5 ? 'var(--green2)' : c.sharpe >= 1 ? 'var(--text)' : 'var(--red)' }}>
                          {c.sharpe?.toFixed(2)}
                        </td>
                        <td className={(c.return_pct || 0) >= 0 ? 'up' : 'down'}>
                          {c.return_pct >= 0 ? '+' : ''}{c.return_pct}%
                        </td>
                        <td style={{ color: 'var(--red)' }}>{c.max_dd}%</td>
                        <td>
                          <span style={{
                            padding: '2px 8px', borderRadius: 4, fontSize: 11, fontWeight: 'bold',
                            background: c.sharpe >= 1.5 ? 'rgba(34,197,94,0.1)' : c.sharpe >= 1 ? 'rgba(234,179,8,0.1)' : 'rgba(239,68,68,0.1)',
                            color: c.sharpe >= 1.5 ? 'var(--green2)' : c.sharpe >= 1 ? 'var(--yellow)' : 'var(--red)',
                          }}>
                            {c.sharpe >= 1.5 ? '优秀' : c.sharpe >= 1 ? '一般' : '较差'}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>

                {/* 快捷回测 */}
                <div style={{ padding: 12, background: 'var(--bg)', borderRadius: 8, border: '1px solid var(--border)' }}>
                  <div style={{ fontWeight: 'bold', marginBottom: 8 }}>快速回测</div>
                  <div style={{ display: 'flex', gap: 8 }}>
                    <button className="btn btn-primary btn-sm"
                      onClick={() => window.open('/api/backtest/run?strategy=breakout&days=252')}>
                      放量突破 1年
                    </button>
                    <button className="btn btn-sm"
                      onClick={() => window.open('/api/backtest/run?strategy=bluechip&days=252')}>
                      蓝筹 1年
                    </button>
                    <button className="btn btn-sm"
                      onClick={() => window.open('/api/backtest/run?strategy=active&days=504')}>
                      活跃 2年
                    </button>
                  </div>
                </div>
              </>
            ) : (
              <p style={{ color: 'var(--text3)', textAlign: 'center', padding: 30 }}>
                点击「生成对比」查看模型 vs 策略回测对比
              </p>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

function StatCard({ label, value, color }) {
  return (
    <div className="stat-card" style={{ textAlign: 'center' }}>
      <div className="stat-label">{label}</div>
      <div className="stat-value" style={{ fontSize: 18, color }}>{value}</div>
    </div>
  )
}

function MetricCard({ label, value, color }) {
  return (
    <div className="stat-card" style={{ textAlign: 'center' }}>
      <div className="stat-label">{label}</div>
      <div className="stat-value" style={{ fontSize: 20, color }}>{value}</div>
    </div>
  )
}
