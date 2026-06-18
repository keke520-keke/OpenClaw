import { useState, useEffect, useCallback } from 'react'
import StockChart from '../components/StockChart'

export default function ChanLunPage() {
  const [code, setCode] = useState('600519')
  const [analysis, setAnalysis] = useState(null)
  const [signals, setSignals] = useState(null)
  const [loading, setLoading] = useState(false)
  const [batchCodes, setBatchCodes] = useState('')
  const [batchResults, setBatchResults] = useState([])
  const [klineData, setKlineData] = useState([])

  const analyzeStock = useCallback(async (stockCode) => {
    if (!stockCode || stockCode.length !== 6) return
    setLoading(true)
    try {
      // 获取真实K线数据
      const px = stockCode.startsWith('6') ? 'sh' : 'sz'
      const klineRes = await fetch(`/api/market/kline/${stockCode}`).then(r => r.json())
      
      if (klineRes.code === 0 && klineRes.data?.length > 0) {
        const realKlineData = klineRes.data.map(d => ({
          date: d.date,
          open: d.open,
          high: d.high,
          low: d.low,
          close: d.close,
          volume: d.volume || 0,
        }))
        setKlineData(realKlineData)
      }
      
      // 获取缠论分析
      const [analysisRes, signalsRes] = await Promise.all([
        fetch(`/api/chanlun/analyze?code=${stockCode}`).then(r => r.json()),
        fetch(`/api/chanlun/signals?code=${stockCode}`).then(r => r.json()),
      ])
      if (analysisRes.code === 0) setAnalysis(analysisRes.data)
      if (signalsRes.code === 0) setSignals(signalsRes.data)
    } catch (e) {
      console.error('分析失败:', e)
    }
    setLoading(false)
  }, [])

  useEffect(() => { analyzeStock(code) }, [code, analyzeStock])

  const batchAnalyze = async () => {
    if (!batchCodes) return
    setLoading(true)
    try {
      const res = await fetch(`/api/chanlun/batch?codes=${batchCodes}`).then(r => r.json())
      if (res.code === 0) setBatchResults(res.data || [])
    } catch (e) {
      console.error('批量分析失败:', e)
    }
    setLoading(false)
  }

  const trendColors = {
    up: 'var(--green2)',
    down: 'var(--red)',
    consolidation: 'var(--yellow)',
    unknown: 'var(--text3)',
  }

  const trendIcons = {
    up: '📈',
    down: '📉',
    consolidation: '📊',
    unknown: '❓',
  }

  return (
    <div>
      <h2 className="page-title">缠论分析</h2>

      {/* 搜索栏 */}
      <div className="card" style={{ marginBottom: 16 }}>
        <div style={{ display: 'flex', gap: 12, alignItems: 'center', flexWrap: 'wrap' }}>
          <div>
            <label style={{ fontSize: 11, color: 'var(--text3)', textTransform: 'uppercase' }}>股票代码</label>
            <input
              type="text"
              value={code}
              onChange={e => setCode(e.target.value)}
              placeholder="输入6位股票代码"
              style={inpStyle}
              maxLength={6}
            />
          </div>
          <button className="btn btn-primary" onClick={() => analyzeStock(code)} disabled={loading}>
            {loading ? '分析中...' : '开始分析'}
          </button>
          <div style={{ marginLeft: 'auto', display: 'flex', gap: 8 }}>
            <input
              type="text"
              value={batchCodes}
              onChange={e => setBatchCodes(e.target.value)}
              placeholder="批量: 600519,000858,300750"
              style={{ ...inpStyle, width: 250 }}
            />
            <button className="btn btn-sm" onClick={batchAnalyze} disabled={loading}>
              批量分析
            </button>
          </div>
        </div>
      </div>

      {/* K线图区域 */}
      {klineData.length > 0 && (
        <div className="card" style={{ marginBottom: 16 }}>
          <div className="card-title">缠论K线图</div>
          <StockChart data={klineData} height={400} />
          <div style={{ marginTop: 8, padding: 12, background: 'var(--bg3)', borderRadius: 8 }}>
            <div style={{ fontSize: 11, color: 'var(--text3)', marginBottom: 8 }}>缠论结构说明</div>
            <div style={{ display: 'flex', gap: 16, fontSize: 12 }}>
              <span><span style={{ color: 'var(--green)' }}>●</span> 笔（连接顶底分型）</span>
              <span><span style={{ color: 'var(--yellow)' }}>■</span> 中枢（多空平衡区）</span>
              <span><span style={{ color: 'var(--cyan)' }}>▲</span> 买点信号</span>
              <span><span style={{ color: 'var(--red)' }}>▼</span> 卖点信号</span>
            </div>
          </div>
        </div>
      )}

      {/* 分析结果 */}
      {analysis && (
        <div className="card-grid" style={{ marginBottom: 16 }}>
          <div className="stat-card">
            <div className="stat-label">当前趋势</div>
            <div className="stat-value" style={{ color: trendColors[analysis.summary?.trend] }}>
              {trendIcons[analysis.summary?.trend]} {analysis.summary?.trend_cn}
            </div>
          </div>
          <div className="stat-card">
            <div className="stat-label">笔数量</div>
            <div className="stat-value">{analysis.summary?.bi_count || 0}</div>
          </div>
          <div className="stat-card">
            <div className="stat-label">中枢数量</div>
            <div className="stat-value">{analysis.summary?.zs_count || 0}</div>
          </div>
          <div className="stat-card">
            <div className="stat-label">当前价格</div>
            <div className="stat-value">{analysis.current_price?.toFixed(2)}</div>
          </div>
        </div>
      )}

      {/* 买卖点信号 */}
      {signals && (
        <div className="grid-2" style={{ marginBottom: 16 }}>
          <div className="card">
            <div className="card-title" style={{ color: 'var(--green)' }}>买点信号</div>
            {signals.signals?.buy?.length > 0 ? (
              signals.signals.buy.map((s, i) => (
                <div key={i} style={{ padding: 12, marginBottom: 8, background: 'rgba(0, 230, 118, 0.1)', borderRadius: 8, border: '1px solid rgba(0, 230, 118, 0.3)' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ fontWeight: 'bold', color: 'var(--green)' }}>{s.type}</span>
                    <span style={{ color: 'var(--green)' }}>{s.price?.toFixed(2)}</span>
                  </div>
                  <div style={{ fontSize: 12, color: 'var(--text3)', marginTop: 4 }}>{s.reason}</div>
                </div>
              ))
            ) : (
              <p style={{ color: 'var(--text3)', textAlign: 'center', padding: 20 }}>暂无买点信号</p>
            )}
          </div>
          <div className="card">
            <div className="card-title" style={{ color: 'var(--red)' }}>卖点信号</div>
            {signals.signals?.sell?.length > 0 ? (
              signals.signals.sell.map((s, i) => (
                <div key={i} style={{ padding: 12, marginBottom: 8, background: 'rgba(255, 23, 68, 0.1)', borderRadius: 8, border: '1px solid rgba(255, 23, 68, 0.3)' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ fontWeight: 'bold', color: 'var(--red)' }}>{s.type}</span>
                    <span style={{ color: 'var(--red)' }}>{s.price?.toFixed(2)}</span>
                  </div>
                  <div style={{ fontSize: 12, color: 'var(--text3)', marginTop: 4 }}>{s.reason}</div>
                </div>
              ))
            ) : (
              <p style={{ color: 'var(--text3)', textAlign: 'center', padding: 20 }}>暂无卖点信号</p>
            )}
          </div>
        </div>
      )}

      {/* 支撑压力位 */}
      {analysis?.summary?.support && (
        <div className="card">
          <div className="card-title">支撑/压力位</div>
          <div style={{ display: 'flex', gap: 24 }}>
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: 11, color: 'var(--text3)', textTransform: 'uppercase', marginBottom: 8 }}>支撑位</div>
              {analysis.summary.support.map((s, i) => (
                <div key={i} style={{ padding: '6px 0', borderBottom: '1px solid var(--border)', color: 'var(--green)', fontFamily: 'monospace' }}>
                  S{i + 1}: {s.toFixed(2)}
                </div>
              ))}
            </div>
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: 11, color: 'var(--text3)', textTransform: 'uppercase', marginBottom: 8 }}>压力位</div>
              {analysis.summary.resistance.map((r, i) => (
                <div key={i} style={{ padding: '6px 0', borderBottom: '1px solid var(--border)', color: 'var(--red)', fontFamily: 'monospace' }}>
                  R{i + 1}: {r.toFixed(2)}
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* 缠论核心概念 */}
      <div className="card" style={{ marginTop: 16 }}>
        <div className="card-title">缠论核心概念</div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 16, fontSize: 13 }}>
          <div>
            <div style={{ fontWeight: 'bold', marginBottom: 4, color: 'var(--green)' }}>分型</div>
            <div style={{ color: 'var(--text3)' }}>顶分型：中间K线高点最高<br/>底分型：中间K线低点最低</div>
          </div>
          <div>
            <div style={{ fontWeight: 'bold', marginBottom: 4, color: 'var(--green)' }}>笔</div>
            <div style={{ color: 'var(--text3)' }}>连接相邻顶底分型<br/>至少包含5根K线</div>
          </div>
          <div>
            <div style={{ fontWeight: 'bold', marginBottom: 4, color: 'var(--green)' }}>中枢</div>
            <div style={{ color: 'var(--text3)' }}>至少3笔的重叠区域<br/>多空力量平衡区</div>
          </div>
          <div>
            <div style={{ fontWeight: 'bold', marginBottom: 4, color: 'var(--green)' }}>买卖点</div>
            <div style={{ color: 'var(--text3)' }}>一买/二买/三买<br/>一卖/二卖/三卖</div>
          </div>
        </div>
      </div>
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
  width: 120,
  fontFamily: 'monospace',
}
