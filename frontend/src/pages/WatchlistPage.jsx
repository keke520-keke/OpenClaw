import { useState, useEffect, useCallback } from 'react'
import { fmt } from '../hooks/useApi'

export default function WatchlistPage({ onSelect }) {
  const [groups, setGroups] = useState([])
  const [stocks, setStocks] = useState([])
  const [activeGroup, setActiveGroup] = useState('')
  const [loading, setLoading] = useState(true)
  const [newGroup, setNewGroup] = useState('')

  // Search
  const [searchQ, setSearchQ] = useState('')
  const [searchResults, setSearchResults] = useState([])
  const [searching, setSearching] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const [g, s] = await Promise.all([
        fetch('/api/watchlist/groups').then(r => r.json()),
        fetch(`/api/watchlist/stocks${activeGroup ? '?group=' + activeGroup : ''}`).then(r => r.json()),
      ])
      setGroups(g.data || [])
      setStocks(s.data || [])
    } catch { }
    finally { setLoading(false) }
  }, [activeGroup])

  useEffect(() => { load() }, [load])

  // Search with debounce
  useEffect(() => {
    if (!searchQ || searchQ.length < 1) { setSearchResults([]); return }
    const t = setTimeout(async () => {
      setSearching(true)
      try {
        const res = await fetch(`/api/market/search?q=${encodeURIComponent(searchQ)}`)
        const d = await res.json()
        setSearchResults(d.data || [])
      } catch { }
      finally { setSearching(false) }
    }, 300)
    return () => clearTimeout(t)
  }, [searchQ])

  const addToWatch = async (code, name) => {
    await fetch(`/api/watchlist/add?code=${code}&name=${encodeURIComponent(name)}&group=${activeGroup || 'default'}`)
    setSearchQ('')
    setSearchResults([])
    load()
  }

  const removeFromWatch = async (code) => {
    await fetch(`/api/watchlist/remove?code=${code}&group=${activeGroup || 'default'}`)
    load()
  }

  const addGroup = async () => {
    if (!newGroup) return
    await fetch(`/api/watchlist/add-group?name=${encodeURIComponent(newGroup)}`)
    setNewGroup('')
    load()
  }

  return (
    <div>
      <h2 className="page-title">自选股</h2>

      {/* 搜索栏 */}
      <div style={{ position: 'relative', marginBottom: 16 }}>
        <div style={{ display: 'flex', gap: 8 }}>
          <input value={searchQ} onChange={e => setSearchQ(e.target.value)}
            placeholder="搜索股票代码或名称..."
            style={{
              flex: 1, padding: '10px 14px', background: 'var(--bg2)',
              border: '1px solid var(--border)', borderRadius: 8, color: 'var(--text)', fontSize: 14,
            }}
            onFocus={() => {}}
          />
          {searching && <span style={{ color: 'var(--text3)', fontSize: 12, alignSelf: 'center' }}>搜索中...</span>}
        </div>

        {/* 搜索结果下拉 */}
        {searchResults.length > 0 && (
          <div style={{
            position: 'absolute', top: '100%', left: 0, right: 0,
            background: 'var(--bg2)', border: '1px solid var(--border)',
            borderRadius: 8, zIndex: 100, maxHeight: 300, overflow: 'auto',
            boxShadow: '0 4px 12px rgba(0,0,0,0.4)',
          }}>
            {searchResults.map(s => (
              <div key={s.code} style={{
                display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                padding: '10px 14px', borderBottom: '1px solid var(--border)',
                cursor: 'pointer',
              }} onClick={() => { setSearchQ(''); setSearchResults([]) }}>
                <div>
                  <span className="link" onClick={(e) => { e.stopPropagation(); onSelect(s.code) }}>
                    {s.code}
                  </span>
                  <span style={{ marginLeft: 8 }}>{s.name}</span>
                </div>
                <button className="btn btn-sm" onClick={(e) => { e.stopPropagation(); addToWatch(s.code, s.name) }}>
                  + 加自选
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      <div style={{ display: 'flex', gap: 20 }}>
        {/* 分组列表 */}
        <div style={{ minWidth: 160 }}>
          <div className="card-title" style={{ marginBottom: 8 }}>分组</div>
          <div key="__all__"
            className="stat-card"
            style={{ marginBottom: 6, cursor: 'pointer',
              border: !activeGroup ? '1px solid var(--blue)' : '1px solid transparent' }}
            onClick={() => setActiveGroup('')}>
            <div style={{ fontWeight: 'bold', fontSize: 13 }}>全部</div>
            <div style={{ fontSize: 11, color: 'var(--text3)' }}>
              {groups.reduce((s, g) => s + g.count, 0)}只
            </div>
          </div>
          {groups.map(g => (
            <div key={g.name}
              className="stat-card"
              style={{ marginBottom: 6, cursor: 'pointer',
                border: activeGroup === g.name ? '1px solid var(--blue)' : '1px solid transparent' }}
              onClick={() => setActiveGroup(g.name)}>
              <div style={{ fontWeight: 'bold', fontSize: 13 }}>{g.name}</div>
              <div style={{ fontSize: 11, color: 'var(--text3)' }}>{g.count}只</div>
            </div>
          ))}
          <div style={{ marginTop: 12 }}>
            <input value={newGroup} onChange={e => setNewGroup(e.target.value)}
              placeholder="新分组名" style={{
                width: '100%', padding: '6px 8px', background: 'var(--bg3)',
                border: '1px solid var(--border)', borderRadius: 4, color: 'var(--text)', fontSize: 12,
                marginBottom: 4,
              }} />
            <button className="btn btn-sm" onClick={addGroup} style={{ width: '100%' }}>+ 新建分组</button>
          </div>
        </div>

        {/* 股票列表 */}
        <div style={{ flex: 1 }}>
          {loading ? (
            <div className="loading">加载中...</div>
          ) : stocks.length === 0 ? (
            <div className="loading">搜索股票添加到自选</div>
          ) : (
            <div style={{ overflowX: 'auto' }}>
              <table>
                <thead><tr>
                  <th>代码</th><th>名称</th><th>价格</th><th>涨跌</th><th>涨跌幅</th>
                  <th>成交额</th><th>换手率</th><th>操作</th>
                </tr></thead>
                <tbody>
                  {stocks.map(s => (
                    <tr key={s.code}>
                      <td><span className="link" onClick={() => onSelect(s.code)}>{s.code}</span></td>
                      <td><span className="link" onClick={() => onSelect(s.code)}>{s.name}</span></td>
                      <td className={(s.pct_chg || s.change_pct || 0) >= 0 ? 'up' : 'down'} style={{ fontWeight: 'bold' }}>
                        {s.price?.toFixed(2)}
                      </td>
                      <td className={(s.pct_chg || s.change_pct || 0) >= 0 ? 'up' : 'down'}>
                        {s.change_amt ? (s.change_amt >= 0 ? '+' : '') + s.change_amt?.toFixed(2) : '-'}
                      </td>
                      <td className={(s.pct_chg || s.change_pct || 0) >= 0 ? 'up' : 'down'} style={{ fontWeight: 'bold' }}>
                        {(s.pct_chg || s.change_pct || 0) >= 0 ? '+' : ''}{(s.pct_chg || s.change_pct || 0)?.toFixed(2)}%
                      </td>
                      <td>{fmt(s.amount)}</td>
                      <td>{s.turnover?.toFixed(2)}%</td>
                      <td>
                        <button className="btn btn-sm" onClick={() => removeFromWatch(s.code)}
                          style={{ color: 'var(--red)', fontSize: 11 }}>
                          移除
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
