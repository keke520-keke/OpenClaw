import { useState, useEffect, useCallback } from 'react'

export default function ScoringPage() {
  const [code, setCode] = useState('600519')
  const [scoreResult, setScoreResult] = useState(null)
  const [topStocks, setTopStocks] = useState([])
  const [loading, setLoading] = useState(false)
  const [minScore, setMinScore] = useState(60)
  const [topLimit, setTopLimit] = useState(10)

  const scoreStock = useCallback(async (stockCode) => {
    if (!stockCode || stockCode.length !== 6) return
    setLoading(true)
    try {
      const res = await fetch(`/api/scoring/score?code=${stockCode}`).then(r => r.json())
      if (res.code === 0) setScoreResult(res.data)
    } catch (e) {
      console.error('评分失败:', e)
    }
    setLoading(false)
  }, [])

  const loadTopStocks = useCallback(async () => {
    setLoading(true)
    try {
      const res = await fetch(`/api/scoring/top?limit=${topLimit}&min_score=${minScore}`).then(r => r.json())
      if (res.code === 0) setTopStocks(res.data || [])
    } catch (e) {
      console.error('加载失败:', e)
    }
    setLoading(false)
  }, [topLimit, minScore])

  useEffect(() => { loadTopStocks() }, [loadTopStocks])

  const getGradeColor = (grade) => {
    switch (grade) {
      case 'A': return 'var(--green2)'
      case 'B': return 'var(--yellow)'
      case 'C': return 'var(--text3)'
      case 'D': return 'var(--red)'
      default: return 'var(--text3)'
    }
  }

  const factorNames = {
    macd_hist_slope: 'MACD斜率',
    obv_trend: 'OBV趋势',
    vwap_deviation: 'VWAP偏离',
    rsi_position: 'RSI位置',
    volume_ratio: '量比',
    price_position: '价格位置',
    market_cap: '市值',
    turnover_quality: '换手质量',
    sector_momentum: '行业动量',
  }

  return (
    <div>
      <h2 className="page-title">多因子打分 (Scoring Engine)</h2>

      {/* 单股评分 */}
      <div className="card" style={{ marginBottom: 16 }}>
        <div className="card-title">单股评分</div>
        <div style={{ display: 'flex', gap: 12, alignItems: 'center', marginBottom: 16 }}>
          <input
            type="text"
            value={code}
            onChange={e => setCode(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && scoreStock(code)}
            placeholder="输入6位股票代码"
            style={inpStyle}
            maxLength={6}
          />
          <button className="btn btn-primary" onClick={() => scoreStock(code)} disabled={loading}>
            {loading ? '评分中...' : '开始评分'}
          </button>
        </div>

        {scoreResult && (
          <div style={{ display: 'grid', gridTemplateColumns: '200px 1fr', gap: 16 }}>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: 48, fontWeight: 'bold', color: getGradeColor(scoreResult.grade) }}>
                {scoreResult.composite_score}
              </div>
              <div style={{ fontSize: 16, color: getGradeColor(scoreResult.grade) }}>
                {scoreResult.grade}级
              </div>
              <div style={{ fontSize: 12, color: 'var(--text3)' }}>{scoreResult.name}</div>
            </div>
            <div>
              <div style={{ fontSize: 12, color: 'var(--text3)', marginBottom: 8 }}>因子得分明细</div>
              {Object.entries(scoreResult.factor_scores || {}).map(([factor, score]) => (
                <div key={factor} style={{ display: 'flex', justifyContent: 'space-between', padding: '4px 0', borderBottom: '1px solid var(--border)' }}>
                  <span style={{ fontSize: 12 }}>{factorNames[factor] || factor}</span>
                  <span style={{ fontSize: 12, color: score >= 70 ? 'var(--green2)' : score >= 40 ? 'var(--yellow)' : 'var(--red)' }}>
                    {score?.toFixed(1)}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* 排行榜 */}
      <div className="card">
        <div className="card-title">多因子排行榜</div>
        <div style={{ display: 'flex', gap: 12, alignItems: 'center', marginBottom: 16 }}>
          <div>
            <label style={{ fontSize: 12, color: 'var(--text3)' }}>最低分数</label>
            <input
              type="number"
              value={minScore}
              onChange={e => setMinScore(parseInt(e.target.value) || 60)}
              style={{ ...inpStyle, width: 60 }}
              min="0"
              max="100"
            />
          </div>
          <div>
            <label style={{ fontSize: 12, color: 'var(--text3)' }}>显示数量</label>
            <input
              type="number"
              value={topLimit}
              onChange={e => setTopLimit(parseInt(e.target.value) || 10)}
              style={{ ...inpStyle, width: 60 }}
              min="1"
              max="50"
            />
          </div>
          <button className="btn btn-sm" onClick={loadTopStocks} disabled={loading}>
            刷新
          </button>
        </div>

        {topStocks.length > 0 ? (
          <table>
            <thead>
              <tr>
                <th>排名</th>
                <th>股票</th>
                <th>综合评分</th>
                <th>评级</th>
                <th>主要因子</th>
              </tr>
            </thead>
            <tbody>
              {topStocks.map((stock, index) => (
                <tr key={stock.code} style={{ cursor: 'pointer' }} onClick={() => { setCode(stock.code); scoreStock(stock.code); }}>
                  <td style={{ fontWeight: 'bold' }}>{index + 1}</td>
                  <td>
                    <strong>{stock.name}</strong>
                    <br /><span style={{ fontSize: 11, color: 'var(--text3)' }}>{stock.code}</span>
                  </td>
                  <td>
                    <span style={{ fontSize: 16, fontWeight: 'bold', color: getGradeColor(stock.grade) }}>
                      {stock.composite_score}
                    </span>
                  </td>
                  <td>
                    <span style={{ 
                      padding: '2px 8px', 
                      borderRadius: 4, 
                      background: getGradeColor(stock.grade),
                      color: '#fff',
                      fontSize: 12,
                      fontWeight: 'bold',
                    }}>
                      {stock.grade}
                    </span>
                  </td>
                  <td style={{ fontSize: 11, color: 'var(--text3)' }}>
                    {Object.entries(stock.factor_scores || {})
                      .sort(([,a], [,b]) => b - a)
                      .slice(0, 3)
                      .map(([factor, score]) => `${factorNames[factor]}:${score?.toFixed(0)}`)
                      .join(', ')}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <p style={{ color: 'var(--text3)', textAlign: 'center', padding: 40 }}>
            {loading ? '加载中...' : '暂无数据'}
          </p>
        )}
      </div>

      {/* 评分说明 */}
      <div className="card" style={{ marginTop: 16 }}>
        <div className="card-title">评分因子说明</div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 12, fontSize: 12 }}>
          {Object.entries(factorNames).map(([key, name]) => (
            <div key={key} style={{ padding: 8, background: 'var(--bg3)', borderRadius: 6 }}>
              <div style={{ fontWeight: 'bold', marginBottom: 4 }}>{name}</div>
              <div style={{ color: 'var(--text3)' }}>
                {key === 'macd_hist_slope' && 'MACD柱状图斜率，正向加速得分高'}
                {key === 'obv_trend' && '能量潮趋势，资金流入得分高'}
                {key === 'vwap_deviation' && '价格相对VWAP偏离度'}
                {key === 'rsi_position' && 'RSI位置，30-70区间得分高'}
                {key === 'volume_ratio' && '量比，2-5倍温和放量最佳'}
                {key === 'price_position' && '价格在K线中的位置'}
                {key === 'market_cap' && '市值，小盘股弹性大'}
                {key === 'turnover_quality' && '换手率，3-8%最健康'}
                {key === 'sector_momentum' && '行业动量，基于涨跌幅'}
              </div>
            </div>
          ))}
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
}
