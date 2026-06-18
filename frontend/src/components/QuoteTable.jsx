import { useState, useEffect, useCallback, useMemo } from 'react'
import { fmt } from '../hooks/useApi'

const PAGE_SIZE = 30

export default function QuoteTable({ onSelect }) {
  const [allData, setAllData] = useState([])
  const [total, setTotal] = useState(0)
  const [sortBy, setSortBy] = useState('amount')
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(true)
  const [source, setSource] = useState('')
  const [searchQuery, setSearchQuery] = useState('')
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    setLoading(true); setError('')
    try {
      const res = await fetch('/api/stock/list')
      const d = await res.json()
      if (d.code === 0) {
        const mapped = d.data.map(r => ({
          ...r,
          change_pct: r.pct_chg ?? r.change_pct ?? 0,
          turnover_rate: r.turnover ?? r.turnover_rate ?? 0,
          amount: r.amount ?? 0,
          volume_ratio: r.volume_ratio ?? 0,
          pre_close: r.pre_close ?? 0,
        }))
        setAllData(mapped)
        setTotal(d.total || mapped.length)
        setSource(d.source || '')
      }
    } catch (e) { console.error(e) }
    finally { setLoading(false) }
  }, [])

  useEffect(() => { load() }, [load])

  // 客户端搜索和排序
  const filteredData = useMemo(() => {
    let arr = [...allData]
    if (searchQuery) {
      const q = searchQuery.toLowerCase()
      arr = arr.filter(r => 
        r.code?.toLowerCase().includes(q) || 
        r.name?.toLowerCase().includes(q)
      )
    }
    arr.sort((a, b) => (b[sortBy] || 0) - (a[sortBy] || 0))
    return arr
  }, [allData, sortBy, searchQuery])

  // 客户端分页
  const pageData = useMemo(() => {
    const start = (page - 1) * PAGE_SIZE
    return filteredData.slice(start, start + PAGE_SIZE)
  }, [filteredData, page])

  const totalPages = Math.max(1, Math.ceil(filteredData.length / PAGE_SIZE))

  return (
    <div>
      <div style={{ display: 'flex', gap: 8, marginBottom: 12, flexWrap: 'wrap', alignItems: 'center' }}>
        <input
          type="text"
          placeholder="搜索股票代码或名称..."
          value={searchQuery}
          onChange={e => { setSearchQuery(e.target.value); setPage(1) }}
          style={{ padding: '6px 12px', background: 'var(--bg3)', border: '1px solid var(--border)', borderRadius: 6, color: 'var(--text)', fontSize: 13, width: 200 }}
        />
        <button className={`btn btn-sm ${sortBy === 'amount' ? 'btn-primary' : ''}`}
          onClick={() => { setSortBy('amount'); setPage(1) }}>成交额</button>
        <button className={`btn btn-sm ${sortBy === 'change_pct' ? 'btn-primary' : ''}`}
          onClick={() => { setSortBy('change_pct'); setPage(1) }}>涨跌幅</button>
        <button className={`btn btn-sm ${sortBy === 'volume' ? 'btn-primary' : ''}`}
          onClick={() => { setSortBy('volume'); setPage(1) }}>成交量</button>
        <button className={`btn btn-sm ${sortBy === 'turnover_rate' ? 'btn-primary' : ''}`}
          onClick={() => { setSortBy('turnover_rate'); setPage(1) }}>换手率</button>
        <button className="btn btn-primary btn-sm" onClick={load} style={{ marginLeft: 'auto' }}>刷新</button>
        {source && <span style={{ fontSize: 11, color: 'var(--text3)' }}>{source}</span>}
      </div>

      {loading ? <div className="loading">加载中...</div> : (
        <>
          <table>
            <thead>
              <tr>
                <th>代码</th><th>名称</th><th>价格</th><th>涨跌幅</th>
                <th>成交额</th><th>成交量</th><th>换手率</th>
              </tr>
            </thead>
            <tbody>
              {pageData.map(r => (
                <tr key={r.code}>
                  <td>{r.code}</td>
                  <td><span className="link" onClick={() => onSelect(r.code)}>{r.name}</span></td>
                  <td className={r.change_pct >= 0 ? 'up' : 'down'}>{r.price?.toFixed(2)}</td>
                  <td className={r.change_pct >= 0 ? 'up' : 'down'}>
                    {r.change_pct >= 0 ? '+' : ''}{r.change_pct?.toFixed(2)}%
                  </td>
                  <td>{fmt(r.amount)}</td>
                  <td>{fmt(r.volume)}</td>
                  <td>{r.turnover_rate?.toFixed(2)}%</td>
                </tr>
              ))}
            </tbody>
          </table>

          <div style={{ display: 'flex', gap: 8, marginTop: 12, alignItems: 'center' }}>
            <button className="btn btn-sm" disabled={page <= 1} onClick={() => setPage(p => p - 1)}>上一页</button>
            <span style={{ color: 'var(--text3)' }}>第{page}页 / 共{totalPages}页 ({total}只)</span>
            <button className="btn btn-sm" disabled={page >= totalPages} onClick={() => setPage(p => p + 1)}>下一页</button>
          </div>
        </>
      )}
    </div>
  )
}
