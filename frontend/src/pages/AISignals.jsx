import { useState } from 'react'
import { useApi } from '../hooks/useApi'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis } from 'recharts'

export default function AISignals() {
  const { data: status, loading } = useApi('/ai/status')
  const { data: backtestConfig } = useApi('/backtest/config-defaults')
  const [showDemo, setShowDemo] = useState(false)

  // 模拟信号数据
  const demoTrades = [
    { code: '600519', name: '贵州茅台', signal: 'STRONG_BUY', score: 0.82, confidence: 0.78, price: '1,811.71' },
    { code: '300750', name: '宁德时代', signal: 'BUY', score: 0.71, confidence: 0.65, price: '219.35' },
    { code: '000858', name: '五粮液', signal: 'BUY', score: 0.68, confidence: 0.60, price: '155.88' },
    { code: '002594', name: '比亚迪', signal: 'HOLD', score: 0.52, confidence: 0.30, price: '268.50' },
    { code: '600036', name: '招商银行', signal: 'HOLD', score: 0.48, confidence: 0.25, price: '38.50' },
    { code: '601318', name: '中国平安', signal: 'SELL', score: 0.35, confidence: 0.55, price: '44.20' },
    { code: '600276', name: '恒瑞医药', signal: 'SELL', score: 0.28, confidence: 0.62, price: '46.80' },
    { code: '601012', name: '隆基绿能', signal: 'STRONG_SELL', score: 0.15, confidence: 0.72, price: '17.30' },
  ]

  const signalColors = {
    STRONG_BUY: 'var(--red)',
    BUY: 'var(--orange)',
    HOLD: 'var(--text2)',
    SELL: 'var(--green)',
    STRONG_SELL: 'var(--green)',
  }

  const featureImportance = [
    { feature: 'T_PRICE_DENSE', importance: 0.041 },
    { feature: 'T_AMOUNT_RATIO', importance: 0.029 },
    { feature: 'T_VOL_CHANGE20', importance: 0.025 },
    { feature: 'T_BIAS60', importance: 0.023 },
    { feature: 'T_RSI14', importance: 0.021 },
    { feature: 'T_MA20_60_DIST', importance: 0.019 },
    { feature: 'T_TURNOVER_ACCUM20', importance: 0.018 },
    { feature: 'T_BOLL_POSITION', importance: 0.017 },
    { feature: 'T_VOL_RATIO', importance: 0.016 },
    { feature: 'T_ATR_RATIO', importance: 0.015 },
  ]

  const modelPerformance = [
    { model: 'RF', accuracy: 72, precision: 68, recall: 65 },
    { model: 'GBM', accuracy: 70, precision: 66, recall: 63 },
    { model: 'LR', accuracy: 65, precision: 62, recall: 60 },
    { model: 'Ensemble', accuracy: 74, precision: 70, recall: 68 },
  ]

  if (loading) return <div className="loading">加载AI引擎...</div>

  return (
    <div>
      <h2 className="page-title">AI 信号</h2>

      {/* AI 状态 */}
      <div className="card-grid" style={{ marginBottom: 16 }}>
        <div className="stat-card">
          <div className="stat-label">引擎状态</div>
          <div className="stat-value" style={{ fontSize: 18, color: status?.trained ? 'var(--green2)' : 'var(--yellow)' }}>
            {status?.trained ? '已训练' : '未训练'}
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-label">模型数量</div>
          <div className="stat-value" style={{ fontSize: 18 }}>{status?.models?.length || 0}</div>
          <div style={{ fontSize: 12, color: 'var(--text3)' }}>{status?.models?.join(', ')}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">特征数</div>
          <div className="stat-value" style={{ fontSize: 18 }}>{status?.features || 0}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">再平衡策略</div>
          <div className="stat-value" style={{ fontSize: 14 }}>{backtestConfig?.config?.rebalance_freq === 'M' ? '月度' : backtestConfig?.config?.rebalance_freq}</div>
          <div style={{ fontSize: 11, color: 'var(--text3)' }}>单只上限{backtestConfig?.config ? (backtestConfig.config.max_position_pct * 100) : 20}%</div>
        </div>
      </div>

      {!showDemo ? (
        <div className="card" style={{ textAlign: 'center', padding: 60 }}>
          <p style={{ color: 'var(--text2)', marginBottom: 20 }}>
            训练 AI 模型生成真实信号，或查看演示数据
          </p>
          <button className="btn btn-primary" onClick={() => setShowDemo(true)}>
            查看演示信号
          </button>
        </div>
      ) : (
        <>
          <div className="grid-2">
            {/* 交易信号 */}
            <div className="card">
              <div className="card-title">当前信号</div>
              <table>
                <thead><tr><th>股票</th><th>信号</th><th>评分</th><th>置信度</th><th>价格</th></tr></thead>
                <tbody>
                  {demoTrades.map(t => (
                    <tr key={t.code}>
                      <td><strong>{t.name}</strong><br /><span style={{ fontSize: 11, color: 'var(--text3)' }}>{t.code}</span></td>
                      <td><span style={{ color: signalColors[t.signal], fontWeight: 'bold', fontSize: 12 }}>{t.signal}</span></td>
                      <td>{(t.score * 100).toFixed(0)}</td>
                      <td>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                          <div style={{ width: 60, height: 6, background: 'var(--bg3)', borderRadius: 3, overflow: 'hidden' }}>
                            <div style={{ width: `${t.confidence * 100}%`, height: '100%', background: 'var(--blue)', borderRadius: 3 }} />
                          </div>
                          {(t.confidence * 100).toFixed(0)}%
                        </div>
                      </td>
                      <td>{t.price}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* 特征重要性 */}
            <div className="card">
              <div className="card-title">Top 10 特征重要性</div>
              <ResponsiveContainer width="100%" height={340}>
                <BarChart data={featureImportance} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                  <XAxis type="number" tick={{ fill: '#6b7280', fontSize: 11 }} tickFormatter={v => `${(v * 100).toFixed(1)}%`} />
                  <YAxis dataKey="feature" type="category" tick={{ fill: '#9ca3af', fontSize: 11 }} width={120} />
                  <Tooltip contentStyle={{ background: '#1f2937', border: '1px solid #374151', borderRadius: 8 }}
                    formatter={v => `${(v * 100).toFixed(2)}%`} />
                  <Bar dataKey="importance" fill="#6366f1" radius={[0, 4, 4, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* 模型性能 */}
          <div className="card">
            <div className="card-title">模型表现对比</div>
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={modelPerformance}>
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                <XAxis dataKey="model" tick={{ fill: '#9ca3af' }} />
                <YAxis tick={{ fill: '#9ca3af' }} domain={[50, 80]} />
                <Tooltip contentStyle={{ background: '#1f2937', border: '1px solid #374151', borderRadius: 8 }} />
                <Bar dataKey="accuracy" name="准确率" fill="#3b82f6" radius={[4, 4, 0, 0]} />
                <Bar dataKey="precision" name="精确率" fill="#22c55e" radius={[4, 4, 0, 0]} />
                <Bar dataKey="recall" name="召回率" fill="#a855f7" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </>
      )}
    </div>
  )
}
