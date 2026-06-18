import { useState, useEffect, useCallback } from 'react'
import StockChart from '../components/StockChart'

export default function IndicatorsPage() {
  const [code, setCode] = useState('600519')
  const [indicators, setIndicators] = useState(null)
  const [klineData, setKlineData] = useState([])
  const [loading, setLoading] = useState(false)
  const [screenerStrategy, setScreenerStrategy] = useState('golden_cross')
  const [screenerResults, setScreenerResults] = useState([])
  const [screenerLoading, setScreenerLoading] = useState(false)
  const [crosshairData, setCrosshairData] = useState(null)

  const calculateIndicators = useCallback(async (stockCode) => {
    if (!stockCode || stockCode.length !== 6) return
    setLoading(true)
    try {
      // 获取真实K线数据
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
      
      // 获取技术指标
      const res = await fetch(`/api/indicators/calculate?code=${stockCode}`).then(r => r.json())
      if (res.code === 0) {
        setIndicators(res.data)
      }
    } catch (e) {
      console.error('计算失败:', e)
    }
    setLoading(false)
  }, [])

  useEffect(() => { calculateIndicators(code) }, [code, calculateIndicators])

  const runScreener = async () => {
    setScreenerLoading(true)
    try {
      const res = await fetch(`/api/screener/technical?strategy=${screenerStrategy}&limit=20`).then(r => r.json())
      if (res.code === 0) setScreenerResults(res.data || [])
    } catch (e) {
      console.error('选股失败:', e)
    }
    setScreenerLoading(false)
  }

  const strategyNames = {
    golden_cross: '金叉策略',
    oversold: '超卖反弹',
    breakout: '突破策略',
    momentum: '动量策略',
    chanlun: '缠论买点',
  }

  const getSignalColor = (signals) => {
    const buyCount = signals?.buy?.length || 0
    const sellCount = signals?.sell?.length || 0
    if (buyCount > sellCount) return 'var(--green2)'
    if (sellCount > buyCount) return 'var(--red)'
    return 'var(--text3)'
  }

  return (
    <div>
      <h2 className="page-title">技术指标分析</h2>

      <div className="card" style={{ marginBottom: 16 }}>
        <div style={{ display: 'flex', gap: 12, alignItems: 'center', flexWrap: 'wrap' }}>
          <div>
            <label style={{ fontSize: 11, color: 'var(--text3)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>股票代码</label>
            <input
              type="text"
              value={code}
              onChange={e => setCode(e.target.value)}
              placeholder="输入6位股票代码"
              style={inpStyle}
              maxLength={6}
            />
          </div>
          <button className="btn btn-primary" onClick={() => calculateIndicators(code)} disabled={loading}>
            {loading ? '分析中...' : '开始分析'}
          </button>
        </div>
      </div>

      {klineData.length > 0 && (
        <div className="card" style={{ marginBottom: 16 }}>
          <div className="card-title">K线图</div>
          <StockChart data={klineData} indicators={indicators || {}} height={400} onCrosshairMove={setCrosshairData} />
          {crosshairData && (
            <div style={{ display: 'flex', gap: 24, marginTop: 8, padding: '8px 12px', background: 'var(--bg3)', borderRadius: 6, fontSize: 12, fontFamily: 'monospace' }}>
              <span style={{ color: 'var(--text3)' }}>日期: {crosshairData.time}</span>
              <span>开盘: {crosshairData.open?.toFixed(2)}</span>
              <span>最高: <span style={{ color: 'var(--green)' }}>{crosshairData.high?.toFixed(2)}</span></span>
              <span>最低: <span style={{ color: 'var(--red)' }}>{crosshairData.low?.toFixed(2)}</span></span>
              <span>收盘: <span style={{ color: crosshairData.close >= crosshairData.open ? 'var(--green)' : 'var(--red)' }}>{crosshairData.close?.toFixed(2)}</span></span>
            </div>
          )}
        </div>
      )}

      {indicators && (
        <div className="card" style={{ marginBottom: 16 }}>
          <div className="card-title">指标数据</div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 12 }}>
            <div style={{ padding: 12, background: 'var(--bg3)', borderRadius: 8 }}>
              <div style={{ fontSize: 11, color: 'var(--text3)', textTransform: 'uppercase' }}>MA5</div>
              <div style={{ fontSize: 16, fontFamily: 'monospace' }}>{indicators.key_indicators?.ma5?.toFixed(2) || '-'}</div>
            </div>
            <div style={{ padding: 12, background: 'var(--bg3)', borderRadius: 8 }}>
              <div style={{ fontSize: 11, color: 'var(--text3)', textTransform: 'uppercase' }}>MA20</div>
              <div style={{ fontSize: 16, fontFamily: 'monospace' }}>{indicators.key_indicators?.ma20?.toFixed(2) || '-'}</div>
            </div>
            <div style={{ padding: 12, background: 'var(--bg3)', borderRadius: 8 }}>
              <div style={{ fontSize: 11, color: 'var(--text3)', textTransform: 'uppercase' }}>RSI(14)</div>
              <div style={{ fontSize: 16, fontFamily: 'monospace', color: indicators.key_indicators?.rsi14 > 70 ? 'var(--red)' : indicators.key_indicators?.rsi14 < 30 ? 'var(--green)' : 'var(--text)' }}>
                {indicators.key_indicators?.rsi14 || '-'}
              </div>
            </div>
            <div style={{ padding: 12, background: 'var(--bg3)', borderRadius: 8 }}>
              <div style={{ fontSize: 11, color: 'var(--text3)', textTransform: 'uppercase' }}>MACD DIF</div>
              <div style={{ fontSize: 16, fontFamily: 'monospace', color: indicators.key_indicators?.macd_dif > 0 ? 'var(--green)' : 'var(--red)' }}>
                {indicators.key_indicators?.macd_dif?.toFixed(4) || '-'}
              </div>
            </div>
          </div>
        </div>
      )}

      <div className="card">
        <div className="card-title">技术选股</div>
        <div style={{ display: 'flex', gap: 12, alignItems: 'center', marginBottom: 16 }}>
          <select value={screenerStrategy} onChange={e => setScreenerStrategy(e.target.value)} style={selStyle}>
            {Object.entries(strategyNames).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          </select>
          <button className="btn btn-primary" onClick={runScreener} disabled={screenerLoading}>
            {screenerLoading ? '筛选中...' : '开始选股'}
          </button>
        </div>
        {screenerResults.length > 0 && (
          <table>
            <thead><tr><th>股票</th><th>价格</th><th>涨跌</th><th>策略</th><th>理由</th></tr></thead>
            <tbody>
              {screenerResults.map((r, i) => (
                <tr key={i} style={{ cursor: 'pointer' }} onClick={() => { setCode(r.code); calculateIndicators(r.code); }}>
                  <td><strong>{r.name}</strong><br/><span style={{ fontSize: 11, color: 'var(--text3)' }}>{r.code}</span></td>
                  <td>{r.price?.toFixed(2)}</td>
                  <td style={{ color: r.change_pct >= 0 ? 'var(--green)' : 'var(--red)' }}>{r.change_pct >= 0 ? '+' : ''}{r.change_pct?.toFixed(2)}%</td>
                  <td>{strategyNames[r.strategy] || r.strategy}</td>
                  <td style={{ fontSize: 12, color: 'var(--text3)' }}>{r.reason}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
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
const selStyle = {
  ...inpStyle,
  marginTop: 0,
}
