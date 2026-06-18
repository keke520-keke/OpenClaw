import { useEffect, useRef } from 'react'
import { createChart, ColorType, CrosshairMode } from 'lightweight-charts'

export default function SubChart({ 
  data = [], 
  type = 'rsi', // 'rsi' or 'macd'
  height = 100,
  color = '#3b82f6',
}) {
  const chartContainerRef = useRef(null)
  const chartRef = useRef(null)
  const seriesRef = useRef(null)

  useEffect(() => {
    if (!chartContainerRef.current) return

    const chart = createChart(chartContainerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: '#0d1117' },
        textColor: '#8a8f98',
        fontSize: 10,
      },
      grid: {
        vertLines: { color: '#1e2430' },
        horzLines: { color: '#1e2430' },
      },
      crosshair: {
        mode: CrosshairMode.Normal,
        vertLine: { color: '#3b82f6', width: 1, style: 0 },
        horzLine: { color: '#3b82f6', width: 1, style: 0 },
      },
      rightPriceScale: {
        borderColor: '#1e2430',
        scaleMargins: { top: 0.1, bottom: 0.1 },
      },
      timeScale: {
        borderColor: '#1e2430',
        visible: false,
      },
      handleScroll: { vertTouchDrag: false },
    })

    chartRef.current = chart

    if (type === 'rsi') {
      // RSI线
      const rsiSeries = chart.addLineSeries({
        color: '#f59e0b',
        lineWidth: 1,
        priceLineVisible: false,
        lastValueVisible: true,
      })
      seriesRef.current = rsiSeries

      // RSI超买超卖线
      chart.addLineSeries({
        color: 'rgba(255, 23, 68, 0.5)',
        lineWidth: 1,
        lineStyle: 2,
        priceLineVisible: false,
        lastValueVisible: false,
      }).setData(data.map(d => ({ time: d.time, value: 70 })))

      chart.addLineSeries({
        color: 'rgba(0, 230, 118, 0.5)',
        lineWidth: 1,
        lineStyle: 2,
        priceLineVisible: false,
        lastValueVisible: false,
      }).setData(data.map(d => ({ time: d.time, value: 30 })))

    } else if (type === 'macd') {
      // MACD柱状图
      const macdSeries = chart.addHistogramSeries({
        priceLineVisible: false,
        lastValueVisible: false,
      })
      seriesRef.current = macdSeries

      // DIF线
      chart.addLineSeries({
        color: '#3b82f6',
        lineWidth: 1,
        priceLineVisible: false,
        lastValueVisible: false,
      }).setData(data.filter(d => d.dif !== undefined).map(d => ({ time: d.time, value: d.dif })))

      // DEA线
      chart.addLineSeries({
        color: '#f59e0b',
        lineWidth: 1,
        priceLineVisible: false,
        lastValueVisible: false,
      }).setData(data.filter(d => d.dea !== undefined).map(d => ({ time: d.time, value: d.dea })))
    }

    const handleResize = () => {
      if (chartContainerRef.current) {
        chart.applyOptions({ 
          width: chartContainerRef.current.clientWidth,
          height: height 
        })
      }
    }
    window.addEventListener('resize', handleResize)
    handleResize()

    return () => {
      window.removeEventListener('resize', handleResize)
      chart.remove()
    }
  }, [height, type])

  useEffect(() => {
    if (!seriesRef.current || !data.length) return

    if (type === 'rsi') {
      const rsiData = data.map(d => ({ time: d.time, value: d.rsi }))
      seriesRef.current.setData(rsiData)
    } else if (type === 'macd') {
      const macdData = data.filter(d => d.histogram !== undefined).map(d => ({
        time: d.time,
        value: d.histogram,
        color: d.histogram >= 0 ? '#00e676' : '#ff1744',
      }))
      seriesRef.current.setData(macdData)
    }

    chartRef.current?.timeScale().fitContent()
  }, [data, type])

  return (
    <div 
      ref={chartContainerRef} 
      style={{ 
        width: '100%', 
        height: height,
        borderRadius: 8,
        overflow: 'hidden',
      }} 
    />
  )
}
