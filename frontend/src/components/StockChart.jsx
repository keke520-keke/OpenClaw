import { useEffect, useRef } from 'react'

export default function StockChart({ data = [], height = 400 }) {
  const containerRef = useRef(null)

  useEffect(() => {
    if (!containerRef.current || !data || data.length === 0) return

    // 清空容器
    containerRef.current.innerHTML = ''

    // 动态加载lightweight-charts
    const script = document.createElement('script')
    script.src = 'https://unpkg.com/lightweight-charts@4.1.0/dist/lightweight-charts.standalone.production.js'
    script.onload = () => {
      if (!window.LightweightCharts || !containerRef.current) return

      const chart = window.LightweightCharts.createChart(containerRef.current, {
        width: containerRef.current.clientWidth,
        height: height,
        layout: {
          background: { type: window.LightweightCharts.ColorType.Solid, color: '#161b22' },
          textColor: '#8b949e',
        },
        grid: {
          vertLines: { color: '#21262d' },
          horzLines: { color: '#21262d' },
        },
        crosshair: { mode: 0 },
        rightPriceScale: { borderColor: '#30363d' },
        timeScale: { borderColor: '#30363d' },
      })

      const candleSeries = chart.addCandlestickSeries({
        upColor: '#00e676',
        downColor: '#ff1744',
        borderUpColor: '#00e676',
        borderDownColor: '#ff1744',
        wickUpColor: '#00e676',
        wickDownColor: '#ff1744',
      })

      candleSeries.setData(data.map(d => ({
        time: d.date,
        open: d.open,
        high: d.high,
        low: d.low,
        close: d.close,
      })))

      const volumeSeries = chart.addHistogramSeries({
        priceFormat: { type: 'volume' },
        priceScaleId: 'volume',
      })
      chart.priceScale('volume').applyOptions({ scaleMargins: { top: 0.8, bottom: 0 } })

      volumeSeries.setData(data.map(d => ({
        time: d.date,
        value: d.volume || 0,
        color: d.close >= d.open ? 'rgba(0,230,118,0.3)' : 'rgba(255,23,68,0.3)',
      })))

      chart.timeScale().fitContent()

      window.addEventListener('resize', () => {
        if (containerRef.current) chart.applyOptions({ width: containerRef.current.clientWidth })
      })
    }
    document.head.appendChild(script)

    return () => {
      if (script.parentNode) script.parentNode.removeChild(script)
    }
  }, [data, height])

  return (
    <div ref={containerRef} style={{ width: '100%', height, borderRadius: 8, overflow: 'hidden', background: '#161b22' }} />
  )
}
