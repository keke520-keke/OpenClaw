import { useState, useEffect, useCallback, useRef } from 'react'

const BASE = '/api'

export function useApi(url, deps) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const depsRef = useRef(deps)

  useEffect(() => { depsRef.current = deps }, [deps])

  const fetchData = useCallback(async () => {
    setLoading(true)
    try {
      const res = await fetch(BASE + url)
      const json = await res.json()
      setData(json.data ?? json)
      setError(null)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [url])

  useEffect(() => { fetchData() }, [fetchData])

  return { data, loading, error, refetch: fetchData }
}

export function useApiPoll(url, interval = 10000) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let active = true
    const fetchData = async () => {
      try {
        const res = await fetch(BASE + url)
        const json = await res.json()
        if (active) { setData(json.data ?? json); setLoading(false) }
      } catch (e) { /* ignore */ }
    }
    fetchData()
    const timer = setInterval(fetchData, interval)
    return () => { active = false; clearInterval(timer) }
  }, [url, interval])

  return { data, loading }
}

export function fmt(n) {
  if (n == null) return '-'
  if (Math.abs(n) >= 1e8) return (n / 1e8).toFixed(2) + '亿'
  if (Math.abs(n) >= 1e4) return (n / 1e4).toFixed(2) + '万'
  return Number(n).toFixed(2)
}
