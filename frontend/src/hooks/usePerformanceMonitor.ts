/**
 * 性能监控Hook - 监控组件性能和用户体验指标
 */
import { useEffect, useCallback, useRef, useState } from 'react'

interface PerformanceMetrics {
  renderTime: number
  memoryUsage?: number
  componentReRenders: number
  lastRenderTimestamp: number
}

interface WebVitalsMetrics {
  lcp?: number // Largest Contentful Paint
  fid?: number // First Input Delay
  cls?: number // Cumulative Layout Shift
  fcp?: number // First Contentful Paint
  ttfb?: number // Time to First Byte
}

export const usePerformanceMonitor = (componentName: string) => {
  const [metrics, setMetrics] = useState<PerformanceMetrics>({
    renderTime: 0,
    componentReRenders: 0,
    lastRenderTimestamp: 0
  })
  const [webVitals, setWebVitals] = useState<WebVitalsMetrics>({})
  
  const renderStartTime = useRef<number>(0)
  const renderCount = useRef<number>(0)
  const observerRef = useRef<PerformanceObserver | null>(null)

  // 开始性能监控
  const startRenderMonitoring = useCallback(() => {
    renderStartTime.current = performance.now()
  }, [])

  // 结束性能监控
  const endRenderMonitoring = useCallback(() => {
    const renderTime = performance.now() - renderStartTime.current
    renderCount.current += 1

    setMetrics(prev => ({
      ...prev,
      renderTime,
      componentReRenders: renderCount.current,
      lastRenderTimestamp: Date.now(),
      memoryUsage: (performance as any).memory?.usedJSHeapSize || 0
    }))

    // 如果渲染时间过长，发出警告
    if (renderTime > 16.67) { // 60fps = 16.67ms per frame
      console.warn(`⚠️ ${componentName} render took ${renderTime.toFixed(2)}ms (>16.67ms target)`)
    }
  }, [componentName])

  // 监控Web Vitals
  useEffect(() => {
    if ('PerformanceObserver' in window) {
      // LCP (Largest Contentful Paint)
      const lcpObserver = new PerformanceObserver((list) => {
        const entries = list.getEntries()
        const lastEntry = entries[entries.length - 1] as PerformanceEntry & {
          startTime: number
        }
        setWebVitals(prev => ({ ...prev, lcp: lastEntry.startTime }))
      })
      lcpObserver.observe({ entryTypes: ['largest-contentful-paint'] })

      // FID (First Input Delay)
      const fidObserver = new PerformanceObserver((list) => {
        const entries = list.getEntries()
        entries.forEach((entry: any) => {
          setWebVitals(prev => ({ 
            ...prev, 
            fid: entry.processingStart - entry.startTime 
          }))
        })
      })
      fidObserver.observe({ entryTypes: ['first-input'] })

      // CLS (Cumulative Layout Shift)
      let clsValue = 0
      const clsObserver = new PerformanceObserver((list) => {
        const entries = list.getEntries()
        entries.forEach((entry: any) => {
          if (!entry.hadRecentInput) {
            clsValue += entry.value
            setWebVitals(prev => ({ ...prev, cls: clsValue }))
          }
        })
      })
      clsObserver.observe({ entryTypes: ['layout-shift'] })

      // Navigation Timing
      if (performance.getEntriesByType) {
        const navEntry = performance.getEntriesByType('navigation')[0] as PerformanceNavigationTiming
        if (navEntry) {
          setWebVitals(prev => ({
            ...prev,
            fcp: navEntry.loadEventStart - navEntry.navigationStart,
            ttfb: navEntry.responseStart - navEntry.navigationStart
          }))
        }
      }

      observerRef.current = lcpObserver
      
      return () => {
        lcpObserver.disconnect()
        fidObserver.disconnect()
        clsObserver.disconnect()
      }
    }
  }, [])

  // 清理
  useEffect(() => {
    return () => {
      if (observerRef.current) {
        observerRef.current.disconnect()
      }
    }
  }, [])

  // 获取性能评分
  const getPerformanceScore = useCallback(() => {
    let score = 100

    // LCP评分 (理想: <2.5s, 需改进: >4s)
    if (webVitals.lcp) {
      if (webVitals.lcp > 4000) score -= 30
      else if (webVitals.lcp > 2500) score -= 15
    }

    // FID评分 (理想: <100ms, 需改进: >300ms)
    if (webVitals.fid) {
      if (webVitals.fid > 300) score -= 25
      else if (webVitals.fid > 100) score -= 10
    }

    // CLS评分 (理想: <0.1, 需改进: >0.25)
    if (webVitals.cls !== undefined) {
      if (webVitals.cls > 0.25) score -= 25
      else if (webVitals.cls > 0.1) score -= 10
    }

    // 组件渲染性能评分
    if (metrics.renderTime > 50) score -= 20
    else if (metrics.renderTime > 20) score -= 10

    return Math.max(0, score)
  }, [webVitals, metrics])

  // 获取性能等级
  const getPerformanceGrade = useCallback(() => {
    const score = getPerformanceScore()
    if (score >= 90) return 'A+'
    if (score >= 80) return 'A'
    if (score >= 70) return 'B'
    if (score >= 60) return 'C'
    return 'D'
  }, [getPerformanceScore])

  // 获取优化建议
  const getOptimizationSuggestions = useCallback(() => {
    const suggestions: string[] = []

    if (webVitals.lcp && webVitals.lcp > 2500) {
      suggestions.push('优化最大内容绘制(LCP)：减少图片大小、启用懒加载、使用CDN')
    }

    if (webVitals.fid && webVitals.fid > 100) {
      suggestions.push('优化首次输入延迟(FID)：减少JavaScript执行时间、使用Web Workers')
    }

    if (webVitals.cls && webVitals.cls > 0.1) {
      suggestions.push('优化累计布局偏移(CLS)：为图片设置尺寸、避免动态插入内容')
    }

    if (metrics.renderTime > 20) {
      suggestions.push('优化组件渲染：使用React.memo、useMemo、useCallback减少重渲染')
    }

    if (metrics.componentReRenders > 10) {
      suggestions.push('减少组件重渲染：检查props和state变化、优化依赖数组')
    }

    return suggestions
  }, [webVitals, metrics])

  return {
    metrics,
    webVitals,
    startRenderMonitoring,
    endRenderMonitoring,
    getPerformanceScore,
    getPerformanceGrade,
    getOptimizationSuggestions
  }
}

// 性能监控装饰器组件
export const withPerformanceMonitoring = <P extends object>(
  WrappedComponent: React.ComponentType<P>,
  componentName: string = WrappedComponent.displayName || WrappedComponent.name || 'Component'
) => {
  const MonitoredComponent = (props: P) => {
    const { startRenderMonitoring, endRenderMonitoring } = usePerformanceMonitor(componentName)

    useEffect(() => {
      startRenderMonitoring()
      return () => {
        endRenderMonitoring()
      }
    })

    return <WrappedComponent {...props} />
  }

  MonitoredComponent.displayName = `withPerformanceMonitoring(${componentName})`
  return MonitoredComponent
}

// 长列表虚拟化Hook
export const useVirtualizedList = (
  items: any[],
  containerHeight: number,
  itemHeight: number
) => {
  const [scrollTop, setScrollTop] = useState(0)
  
  const startIndex = Math.floor(scrollTop / itemHeight)
  const endIndex = Math.min(
    startIndex + Math.ceil(containerHeight / itemHeight) + 1,
    items.length
  )
  
  const visibleItems = items.slice(startIndex, endIndex)
  const offsetY = startIndex * itemHeight
  
  return {
    visibleItems,
    startIndex,
    endIndex,
    offsetY,
    totalHeight: items.length * itemHeight,
    setScrollTop
  }
}

// 图片懒加载Hook
export const useLazyImage = (src: string, placeholder?: string) => {
  const [imageSrc, setImageSrc] = useState(placeholder || '')
  const [isLoaded, setIsLoaded] = useState(false)
  const [isError, setIsError] = useState(false)
  const imgRef = useRef<HTMLImageElement>(null)

  useEffect(() => {
    let observer: IntersectionObserver | undefined

    if (imgRef.current) {
      observer = new IntersectionObserver(
        (entries) => {
          entries.forEach((entry) => {
            if (entry.isIntersecting) {
              const img = new Image()
              img.onload = () => {
                setImageSrc(src)
                setIsLoaded(true)
              }
              img.onerror = () => {
                setIsError(true)
              }
              img.src = src
              observer?.disconnect()
            }
          })
        },
        { threshold: 0.1 }
      )

      observer.observe(imgRef.current)
    }

    return () => {
      observer?.disconnect()
    }
  }, [src])

  return {
    ref: imgRef,
    src: imageSrc,
    isLoaded,
    isError
  }
}

// 防抖Hook
export const useDebounce = <T>(value: T, delay: number) => {
  const [debouncedValue, setDebouncedValue] = useState<T>(value)

  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value)
    }, delay)

    return () => {
      clearTimeout(handler)
    }
  }, [value, delay])

  return debouncedValue
}

// 节流Hook
export const useThrottle = <T extends (...args: any[]) => any>(
  fn: T,
  delay: number
): T => {
  const lastRun = useRef(Date.now())

  return useCallback(
    ((...args) => {
      if (Date.now() - lastRun.current >= delay) {
        fn(...args)
        lastRun.current = Date.now()
      }
    }) as T,
    [fn, delay]
  )
}