import { useState, useEffect, useCallback, useRef } from 'react'

export default function LogPage() {
  const [logs, setLogs] = useState([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [pageSize] = useState(50)
  const [filterLevel, setFilterLevel] = useState('')
  const [filterModule, setFilterModule] = useState('')
  const [search, setSearch] = useState('')
  const [autoRefresh, setAutoRefresh] = useState(false)
  const [loading, setLoading] = useState(false)
  const timerRef = useRef(null)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const params = new URLSearchParams()
      if (filterLevel) params.set('level', filterLevel)
      if (filterModule) params.set('module', filterModule)
      if (search) params.set('search', search)
      params.set('page', page)
      params.set('page_size', pageSize)
      const res = await fetch(`/api/logs?${params}`)
      const d = await res.json()
      if (d.code === 0) {
        setLogs(d.data || [])
        setTotal(d.total || 0)
      }
    } catch { }
    finally { setLoading(false) }
  }, [filterLevel, filterModule, search, page, pageSize])

  useEffect(() => { load() }, [load])

  useEffect(() => {
    if (autoRefresh) {
      timerRef.current = setInterval(() => load(), 30000)
    }
    return () => { if (timerRef.current) clearInterval(timerRef.current) }
  }, [autoRefresh, load])

  const levelColors = {
    INFO: { color: 'var(--text2)', bg: 'transparent' },
    WARN: { color: 'var(--yellow)', bg: 'rgba(234,179,8,0.06)' },
    ERROR: { color: 'var(--red)', bg: 'rgba(239,68,68,0.06)' },
    ALERT: { color: 'var(--red)', bg: 'rgba(239,68,68,0.08)' },
  }

  const moduleLabels = {
    TRADE: '交易', RISK: '风控', AUTO: '自动', ALERT: '预警', SYSTEM: '系统',
  }

  const totalPages = Math.max(1, Math.ceil(total / pageSize))

  return (
    <div>
      <h2 className="page-title">日志告警</h2>

      {/* 统计 */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 12, marginBottom: 16 }}>
        <div className="stat-card" style={{ textAlign: 'center' }}>
          <div className="stat-label">总日志</div>
          <div className="stat-value" style={{ fontSize: 20 }}>{total}</div>
        </div>
        <div className="stat-card" style={{ textAlign: 'center' }}>
          <div className="stat-label">ERROR</div>
          <div className="stat-value" style={{ fontSize: 20, color: logs.filter(l => l.level === 'ERROR' || l.level === 'ALERT').length > 0 ? 'var(--red)' : 'var(--text)' }}>
            {logs.filter(l => l.level === 'ERROR' || l.level === 'ALERT').length}
          </div>
        </div>
        <div className="stat-card" style={{ textAlign: 'center' }}>
          <div className="stat-label">WARNING</div>
          <div className="stat-value" style={{ fontSize: 20, color: 'var(--yellow)' }}>
            {logs.filter(l => l.level === 'WARN').length}
          </div>
        </div>
        <div className="stat-card" style={{ textAlign: 'center' }}>
          <div className="stat-label">INFO</div>
          <div className="stat-value" style={{ fontSize: 20 }}>
            {logs.filter(l => l.level === 'INFO').length}
          </div>
        </div>
        <div className="stat-card" style={{ textAlign: 'center' }}>
          <div className="stat-label">实时刷新</div>
          <div style={{ marginTop: 8 }}>
            <button className={`btn btn-sm ${autoRefresh ? 'btn-primary' : ''}`}
              onClick={() => setAutoRefresh(!autoRefresh)}>
              {autoRefresh ? '关闭' : '开启'}
            </button>
          </div>
        </div>
      </div>

      {/* 筛选栏 */}
      <div className="card" style={{ marginBottom: 16, padding: '12px 16px' }}>
        <div style={{ display: 'flex', gap: 12, alignItems: 'center', flexWrap: 'wrap' }}>
          <span style={{ fontSize: 12, color: 'var(--text3)' }}>级别</span>
          {[['','全部'],['INFO','INFO'],['WARN','WARN'],['ERROR','ERROR'],['ALERT','ALERT']].map(([v,l]) => (
            <button key={v} className={`btn btn-sm ${filterLevel === v ? 'btn-primary' : ''}`}
              onClick={() => { setFilterLevel(v); setPage(1) }}
              style={{ padding: '3px 10px', fontSize: 12,
                color: v === 'ERROR' || v === 'ALERT' ? 'var(--red)' : v === 'WARN' ? 'var(--yellow)' : 'var(--text)' }}>
              {l}
            </button>
          ))}
          <span style={{ fontSize: 12, color: 'var(--text3)', marginLeft: 12 }}>模块</span>
          {[['','全部'],['TRADE','交易'],['RISK','风控'],['AUTO','自动'],['ALERT','预警']].map(([v,l]) => (
            <button key={v} className={`btn btn-sm ${filterModule === v ? 'btn-primary' : ''}`}
              onClick={() => { setFilterModule(v); setPage(1) }} style={{ padding: '3px 10px', fontSize: 12 }}>{l}</button>
          ))}
          <span style={{ fontSize: 12, color: 'var(--text3)', marginLeft: 12 }}>搜索</span>
          <input value={search} onChange={e => { setSearch(e.target.value); setPage(1) }}
            placeholder="关键词..." style={{
              padding: '3px 10px', background: 'var(--bg3)', border: '1px solid var(--border)',
              borderRadius: 4, color: 'var(--text)', fontSize: 12, width: 150,
            }} />
          <button className="btn btn-sm" onClick={load} style={{ marginLeft: 'auto' }}>刷新</button>
        </div>
      </div>

      {/* 日志列表 */}
      <div className="card">
        <div className="card-title">日志列表（共{total}条）</div>
        {logs.length === 0 ? (
          <p style={{ color: 'var(--text3)', textAlign: 'center', padding: 40 }}>暂无日志</p>
        ) : (
          <div style={{ maxHeight: 600, overflow: 'auto' }}>
            {logs.map((log, i) => {
              const lc = levelColors[log.level] || levelColors.INFO
              return (
                <div key={i} style={{
                  display: 'flex', gap: 8, padding: '6px 8px',
                  borderBottom: '1px solid var(--border)', fontSize: 13,
                  background: lc.bg,
                }}>
                  <span style={{ color: 'var(--text3)', minWidth: 80, flexShrink: 0, fontFamily: 'monospace', fontSize: 12 }}>
                    {log.time?.slice(11)}
                  </span>
                  <span style={{
                    color: lc.color, fontWeight: 'bold', minWidth: 50, flexShrink: 0,
                    fontSize: 11, padding: '1px 6px', borderRadius: 3,
                    background: lc.bg, border: `1px solid ${lc.color}33`,
                    textAlign: 'center',
                  }}>
                    {log.level}
                  </span>
                  <span style={{ color: '#6366f1', minWidth: 40, flexShrink: 0, fontSize: 12 }}>
                    [{moduleLabels[log.module] || log.module || '-'}]
                  </span>
                  <span style={{ color: lc.color, flex: 1, wordBreak: 'break-all' }}>
                    {log.msg}
                  </span>
                </div>
              )
            })}
          </div>
        )}

        {/* 分页 */}
        {totalPages > 1 && (
          <div style={{ display: 'flex', gap: 8, marginTop: 12, alignItems: 'center' }}>
            <button className="btn btn-sm" disabled={page <= 1} onClick={() => setPage(p => p - 1)}>上一页</button>
            <span style={{ color: 'var(--text3)', fontSize: 12 }}>第{page}页 / 共{totalPages}页</span>
            <button className="btn btn-sm" disabled={page >= totalPages} onClick={() => setPage(p => p + 1)}>下一页</button>
          </div>
        )}
      </div>
    </div>
  )
}
