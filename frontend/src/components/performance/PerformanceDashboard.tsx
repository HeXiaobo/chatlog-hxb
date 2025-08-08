/**
 * 性能监控仪表板 - 实时显示系统性能指标
 */
import React, { useEffect, useState, useMemo } from 'react'
import { Card, Row, Col, Progress, Statistic, Alert, Tooltip, Switch } from 'antd'
import { 
  DashboardOutlined, 
  ThunderboltOutlined, 
  MemoryStick, 
  ClockCircleOutlined,
  WarningOutlined,
  CheckCircleOutlined
} from '@ant-design/icons'
import { usePerformanceMonitor } from '../../hooks/usePerformanceMonitor'

interface PerformanceDashboardProps {
  showAdvanced?: boolean
  autoRefresh?: boolean
  refreshInterval?: number
}

const PerformanceDashboard: React.FC<PerformanceDashboardProps> = ({
  showAdvanced = false,
  autoRefresh = true,
  refreshInterval = 5000
}) => {
  const { 
    metrics, 
    webVitals, 
    getPerformanceScore, 
    getPerformanceGrade,
    getOptimizationSuggestions 
  } = usePerformanceMonitor('PerformanceDashboard')

  const [realTimeStats, setRealTimeStats] = useState({
    memoryUsage: 0,
    fps: 60,
    networkLatency: 0,
    cacheHitRate: 0
  })

  const [isMonitoring, setIsMonitoring] = useState(autoRefresh)

  // 实时性能数据采集
  useEffect(() => {
    if (!isMonitoring) return

    const interval = setInterval(() => {
      // 内存使用情况
      const memory = (performance as any).memory
      if (memory) {
        const memoryUsage = (memory.usedJSHeapSize / memory.totalJSHeapSize) * 100
        setRealTimeStats(prev => ({
          ...prev,
          memoryUsage
        }))
      }

      // 模拟FPS监控（实际应用中需要使用requestAnimationFrame）
      const fps = Math.floor(Math.random() * 10) + 55 // 模拟55-65fps
      setRealTimeStats(prev => ({
        ...prev,
        fps
      }))

      // 网络延迟监控（简化版）
      const start = performance.now()
      fetch('/api/v1/categories', { method: 'HEAD' })
        .then(() => {
          const latency = performance.now() - start
          setRealTimeStats(prev => ({
            ...prev,
            networkLatency: latency
          }))
        })
        .catch(() => {
          setRealTimeStats(prev => ({
            ...prev,
            networkLatency: 999
          }))
        })

      // 缓存命中率（模拟）
      const cacheHitRate = Math.floor(Math.random() * 20) + 70 // 模拟70-90%
      setRealTimeStats(prev => ({
        ...prev,
        cacheHitRate
      }))
    }, refreshInterval)

    return () => clearInterval(interval)
  }, [isMonitoring, refreshInterval])

  // 性能评分和建议
  const performanceScore = useMemo(() => getPerformanceScore(), [getPerformanceScore])
  const performanceGrade = useMemo(() => getPerformanceGrade(), [getPerformanceGrade])
  const suggestions = useMemo(() => getOptimizationSuggestions(), [getOptimizationSuggestions])

  // 性能状态颜色
  const getStatusColor = (value: number, thresholds: [number, number]) => {
    if (value >= thresholds[1]) return '#52c41a' // 绿色 - 优秀
    if (value >= thresholds[0]) return '#faad14' // 黄色 - 良好
    return '#ff4d4f' // 红色 - 需改进
  }

  return (
    <div className="performance-dashboard">
      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col span={24}>
          <Card
            title={
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <span>
                  <DashboardOutlined /> 性能监控仪表板
                </span>
                <Switch
                  checked={isMonitoring}
                  onChange={setIsMonitoring}
                  checkedChildren="实时监控"
                  unCheckedChildren="已暂停"
                />
              </div>
            }
            size="small"
          >
            <Alert
              message={`总体性能评分: ${performanceGrade} (${performanceScore}分)`}
              type={performanceScore >= 80 ? 'success' : performanceScore >= 60 ? 'warning' : 'error'}
              showIcon
              style={{ marginBottom: 16 }}
            />
          </Card>
        </Col>
      </Row>

      {/* 核心Web Vitals */}
      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col xs={24} sm={12} md={6}>
          <Card size="small" title="最大内容绘制 (LCP)">
            <Tooltip title="理想值 < 2.5s，需改进 > 4s">
              <Statistic
                value={webVitals.lcp ? (webVitals.lcp / 1000).toFixed(2) : '0'}
                suffix="s"
                valueStyle={{ 
                  color: webVitals.lcp ? getStatusColor(webVitals.lcp, [2500, 4000]) : '#666'
                }}
              />
            </Tooltip>
          </Card>
        </Col>

        <Col xs={24} sm={12} md={6}>
          <Card size="small" title="首次输入延迟 (FID)">
            <Tooltip title="理想值 < 100ms，需改进 > 300ms">
              <Statistic
                value={webVitals.fid ? webVitals.fid.toFixed(0) : '0'}
                suffix="ms"
                valueStyle={{ 
                  color: webVitals.fid ? getStatusColor(webVitals.fid, [100, 300]) : '#666'
                }}
              />
            </Tooltip>
          </Card>
        </Col>

        <Col xs={24} sm={12} md={6}>
          <Card size="small" title="累计布局偏移 (CLS)">
            <Tooltip title="理想值 < 0.1，需改进 > 0.25">
              <Statistic
                value={webVitals.cls ? webVitals.cls.toFixed(3) : '0.000'}
                valueStyle={{ 
                  color: webVitals.cls ? getStatusColor(webVitals.cls * 1000, [100, 250]) : '#666'
                }}
              />
            </Tooltip>
          </Card>
        </Col>

        <Col xs={24} sm={12} md={6}>
          <Card size="small" title="首字节时间 (TTFB)">
            <Tooltip title="理想值 < 600ms，需改进 > 1s">
              <Statistic
                value={webVitals.ttfb ? (webVitals.ttfb / 1000).toFixed(2) : '0'}
                suffix="s"
                valueStyle={{ 
                  color: webVitals.ttfb ? getStatusColor(webVitals.ttfb, [600, 1000]) : '#666'
                }}
              />
            </Tooltip>
          </Card>
        </Col>
      </Row>

      {/* 实时性能指标 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col xs={24} sm={12} md={6}>
          <Card size="small" title={<><MemoryStick /> 内存使用</>}>
            <Progress
              percent={Math.round(realTimeStats.memoryUsage)}
              status={realTimeStats.memoryUsage > 80 ? 'exception' : 'success'}
              format={(percent) => `${percent}%`}
            />
          </Card>
        </Col>

        <Col xs={24} sm={12} md={6}>
          <Card size="small" title={<><ThunderboltOutlined /> 渲染性能</>}>
            <Statistic
              value={realTimeStats.fps}
              suffix="FPS"
              valueStyle={{ 
                color: getStatusColor(realTimeStats.fps, [45, 55])
              }}
            />
          </Card>
        </Col>

        <Col xs={24} sm={12} md={6}>
          <Card size="small" title={<><ClockCircleOutlined /> 网络延迟</>}>
            <Statistic
              value={realTimeStats.networkLatency.toFixed(0)}
              suffix="ms"
              valueStyle={{ 
                color: getStatusColor(1000 - realTimeStats.networkLatency, [800, 900])
              }}
            />
          </Card>
        </Col>

        <Col xs={24} sm={12} md={6}>
          <Card size="small" title="缓存命中率">
            <Progress
              percent={realTimeStats.cacheHitRate}
              status={realTimeStats.cacheHitRate > 80 ? 'success' : 'normal'}
              format={(percent) => `${percent}%`}
            />
          </Card>
        </Col>
      </Row>

      {/* 高级性能指标 */}
      {showAdvanced && (
        <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
          <Col span={24}>
            <Card size="small" title="高级性能指标">
              <Row gutter={16}>
                <Col span={8}>
                  <Statistic
                    title="组件重渲染次数"
                    value={metrics.componentReRenders}
                    prefix={metrics.componentReRenders > 10 ? <WarningOutlined /> : <CheckCircleOutlined />}
                  />
                </Col>
                <Col span={8}>
                  <Statistic
                    title="最后渲染时间"
                    value={metrics.renderTime.toFixed(2)}
                    suffix="ms"
                  />
                </Col>
                <Col span={8}>
                  <Statistic
                    title="内存堆大小"
                    value={metrics.memoryUsage ? (metrics.memoryUsage / 1024 / 1024).toFixed(2) : '0'}
                    suffix="MB"
                  />
                </Col>
              </Row>
            </Card>
          </Col>
        </Row>
      )}

      {/* 优化建议 */}
      {suggestions.length > 0 && (
        <Row gutter={[16, 16]}>
          <Col span={24}>
            <Card size="small" title={<><WarningOutlined /> 性能优化建议</>}>
              {suggestions.map((suggestion, index) => (
                <Alert
                  key={index}
                  message={suggestion}
                  type="info"
                  showIcon
                  style={{ marginBottom: index < suggestions.length - 1 ? 8 : 0 }}
                />
              ))}
            </Card>
          </Col>
        </Row>
      )}
    </div>
  )
}

export default React.memo(PerformanceDashboard)