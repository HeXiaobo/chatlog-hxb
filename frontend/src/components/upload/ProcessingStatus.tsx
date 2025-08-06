import React, { useState, useEffect, useCallback } from 'react'
import { 
  Card, 
  Steps, 
  Progress, 
  Alert, 
  Button, 
  Space, 
  Typography,
  Statistic,
  Divider,
  Timeline,
  Tag
} from 'antd'
import {
  CloudUploadOutlined,
  FileSearchOutlined,
  TagsOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  LoadingOutlined,
  ClockCircleOutlined,
  FileTextOutlined,
  DatabaseOutlined
} from '@ant-design/icons'
import type { UploadHistory, APIResponse } from '../../types'
import api from '../../services/api'

const { Step } = Steps
const { Text, Title } = Typography

interface ProcessingStatusProps {
  uploadId?: number
  onComplete?: (result: UploadHistory) => void
  onError?: (error: string) => void
  onCancel?: () => void
  autoRefresh?: boolean
  refreshInterval?: number
}

interface ProcessingStep {
  key: string
  title: string
  description: string
  icon: React.ReactNode
  status: 'wait' | 'process' | 'finish' | 'error'
}

interface ProcessingStats {
  totalMessages: number
  processedMessages: number
  extractedQAs: number
  skippedMessages: number
  processingSpeed: number
  estimatedTimeRemaining: number
}

const ProcessingStatus: React.FC<ProcessingStatusProps> = ({
  uploadId,
  onComplete,
  onError,
  onCancel,
  autoRefresh = true,
  refreshInterval = 2000
}) => {
  const [uploadStatus, setUploadStatus] = useState<UploadHistory | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [stats, setStats] = useState<ProcessingStats | null>(null)
  const [logs, setLogs] = useState<Array<{ time: string; message: string; type: 'info' | 'success' | 'warning' | 'error' }>>([])

  const processSteps: ProcessingStep[] = [
    {
      key: 'upload',
      title: '文件上传',
      description: '上传JSON文件到服务器',
      icon: <CloudUploadOutlined />,
      status: 'finish'
    },
    {
      key: 'parsing',
      title: '解析文件',
      description: '读取和验证JSON格式',
      icon: <FileSearchOutlined />,
      status: uploadStatus?.status === 'processing' ? 'process' : uploadStatus?.status === 'completed' ? 'finish' : 'wait'
    },
    {
      key: 'extraction',
      title: '提取问答',
      description: '识别对话中的问答对',
      icon: <FileTextOutlined />,
      status: uploadStatus?.status === 'processing' ? 'process' : uploadStatus?.status === 'completed' ? 'finish' : 'wait'
    },
    {
      key: 'classification',
      title: '自动分类',
      description: '为问答对分配适当分类',
      icon: <TagsOutlined />,
      status: uploadStatus?.status === 'processing' ? 'process' : uploadStatus?.status === 'completed' ? 'finish' : 'wait'
    },
    {
      key: 'storage',
      title: '入库保存',
      description: '将结果保存到数据库',
      icon: <DatabaseOutlined />,
      status: uploadStatus?.status === 'completed' ? 'finish' : uploadStatus?.status === 'error' ? 'error' : 'wait'
    }
  ]

  const fetchUploadStatus = useCallback(async () => {
    if (!uploadId) return

    setLoading(true)
    try {
      const response = await api.get<APIResponse<UploadHistory>>(`/upload/status/${uploadId}`)
      
      if (response.data.success && response.data.data) {
        const status = response.data.data
        setUploadStatus(status)

        // 模拟处理统计数据（实际应该从后端获取）
        if (status.status === 'processing') {
          setStats({
            totalMessages: status.total_messages || 0,
            processedMessages: Math.floor((status.total_messages || 0) * 0.6),
            extractedQAs: Math.floor((status.extracted_qa_count || 0) * 0.8),
            skippedMessages: Math.floor((status.total_messages || 0) * 0.1),
            processingSpeed: 50, // 每秒处理消息数
            estimatedTimeRemaining: 30 // 预计剩余秒数
          })
        }

        // 添加日志条目
        const now = new Date().toLocaleTimeString()
        if (status.status === 'completed') {
          setLogs(prev => [...prev, {
            time: now,
            message: `处理完成，共提取 ${status.extracted_qa_count} 条问答`,
            type: 'success'
          }])
          onComplete?.(status)
        } else if (status.status === 'error') {
          setLogs(prev => [...prev, {
            time: now,
            message: `处理失败：${status.error_message}`,
            type: 'error'
          }])
          onError?.(status.error_message || '处理失败')
        } else {
          setLogs(prev => [...prev, {
            time: now,
            message: '正在处理中...',
            type: 'info'
          }])
        }

        if (status.status === 'error') {
          setError(status.error_message || '处理失败')
        }
      }
    } catch (err: any) {
      const errorMsg = err.response?.data?.error?.message || err.message || '获取状态失败'
      setError(errorMsg)
      onError?.(errorMsg)
    } finally {
      setLoading(false)
    }
  }, [uploadId, onComplete, onError])

  useEffect(() => {
    if (!uploadId || !autoRefresh) return

    fetchUploadStatus()
    
    const interval = setInterval(() => {
      if (uploadStatus?.status === 'processing') {
        fetchUploadStatus()
      }
    }, refreshInterval)

    return () => clearInterval(interval)
  }, [uploadId, autoRefresh, refreshInterval, uploadStatus?.status, fetchUploadStatus])

  const getCurrentStepIndex = useCallback((): number => {
    if (!uploadStatus) return 0
    
    switch (uploadStatus.status) {
      case 'processing':
        return 2 // 正在提取问答
      case 'completed':
        return 4 // 全部完成
      case 'error':
        return 2 // 在处理阶段出错
      default:
        return 0
    }
  }, [uploadStatus])

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 B'
    const k = 1024
    const sizes = ['B', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
  }

  const formatDuration = (seconds: number): string => {
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return mins > 0 ? `${mins}分${secs}秒` : `${secs}秒`
  }

  if (error && !uploadStatus) {
    return (
      <Card title="处理状态">
        <Alert
          message="获取处理状态失败"
          description={error}
          type="error"
          showIcon
          action={
            <Button size="small" onClick={fetchUploadStatus}>
              重试
            </Button>
          }
        />
      </Card>
    )
  }

  return (
    <Card
      title={
        <Space>
          <span>文件处理状态</span>
          {uploadStatus?.status === 'processing' && <LoadingOutlined />}
          {uploadStatus?.status === 'completed' && <CheckCircleOutlined style={{ color: '#52c41a' }} />}
          {uploadStatus?.status === 'error' && <ExclamationCircleOutlined style={{ color: '#f5222d' }} />}
        </Space>
      }
      loading={loading && !uploadStatus}
    >
      {uploadStatus && (
        <div className="processing-status">
          {/* 文件基本信息 */}
          <div className="file-info">
            <Space size="large">
              <div>
                <Text type="secondary">文件名：</Text>
                <Text strong>{uploadStatus.filename}</Text>
              </div>
              <div>
                <Text type="secondary">文件大小：</Text>
                <Text>{formatFileSize(uploadStatus.file_size)}</Text>
              </div>
              <div>
                <Text type="secondary">状态：</Text>
                <Tag color={
                  uploadStatus.status === 'completed' ? 'success' :
                  uploadStatus.status === 'error' ? 'error' : 'processing'
                }>
                  {uploadStatus.status === 'completed' ? '已完成' :
                   uploadStatus.status === 'error' ? '处理失败' : '处理中'}
                </Tag>
              </div>
            </Space>
          </div>

          <Divider />

          {/* 处理步骤 */}
          <div className="process-steps">
            <Steps current={getCurrentStepIndex()} status={uploadStatus.status === 'error' ? 'error' : undefined}>
              {processSteps.map(step => (
                <Step
                  key={step.key}
                  title={step.title}
                  description={step.description}
                  icon={step.icon}
                />
              ))}
            </Steps>
          </div>

          {/* 处理中的详细信息 */}
          {uploadStatus.status === 'processing' && stats && (
            <>
              <Divider />
              <div className="processing-details">
                <Space direction="vertical" style={{ width: '100%' }}>
                  <div>
                    <Text strong>处理进度</Text>
                    <Progress 
                      percent={Math.round((stats.processedMessages / stats.totalMessages) * 100)}
                      status="active"
                      strokeColor="#1890ff"
                    />
                  </div>
                  
                  <div className="stats-row">
                    <Space size="large" wrap>
                      <Statistic 
                        title="总消息数" 
                        value={stats.totalMessages} 
                        prefix={<FileTextOutlined />}
                      />
                      <Statistic 
                        title="已处理" 
                        value={stats.processedMessages} 
                        prefix={<CheckCircleOutlined />}
                      />
                      <Statistic 
                        title="已提取" 
                        value={stats.extractedQAs} 
                        prefix={<TagsOutlined />}
                        valueStyle={{ color: '#3f8600' }}
                      />
                      <Statistic 
                        title="预计剩余" 
                        value={stats.estimatedTimeRemaining} 
                        suffix="秒"
                        prefix={<ClockCircleOutlined />}
                      />
                    </Space>
                  </div>
                </Space>
              </div>
            </>
          )}

          {/* 处理完成结果 */}
          {uploadStatus.status === 'completed' && (
            <>
              <Divider />
              <div className="completion-results">
                <Alert
                  message="处理完成"
                  description={`成功处理 ${uploadStatus.total_messages} 条消息，提取出 ${uploadStatus.extracted_qa_count} 条问答记录`}
                  type="success"
                  showIcon
                  style={{ marginBottom: 16 }}
                />
                
                <Space size="large">
                  <Statistic 
                    title="消息总数" 
                    value={uploadStatus.total_messages || 0} 
                    prefix={<FileTextOutlined />}
                  />
                  <Statistic 
                    title="提取问答" 
                    value={uploadStatus.extracted_qa_count || 0} 
                    prefix={<CheckCircleOutlined />}
                    valueStyle={{ color: '#3f8600' }}
                  />
                  <Statistic 
                    title="提取率" 
                    value={uploadStatus.total_messages ? 
                      Math.round(((uploadStatus.extracted_qa_count || 0) / uploadStatus.total_messages) * 100) : 0
                    } 
                    suffix="%"
                    prefix={<TagsOutlined />}
                  />
                </Space>
              </div>
            </>
          )}

          {/* 错误信息 */}
          {uploadStatus.status === 'error' && (
            <>
              <Divider />
              <Alert
                message="处理失败"
                description={uploadStatus.error_message || '未知错误'}
                type="error"
                showIcon
                action={
                  <Button size="small" onClick={fetchUploadStatus}>
                    重新获取状态
                  </Button>
                }
              />
            </>
          )}

          {/* 处理日志 */}
          {logs.length > 0 && (
            <>
              <Divider />
              <div className="processing-logs">
                <Text strong>处理日志</Text>
                <Timeline
                  style={{ marginTop: 12 }}
                  items={logs.map(log => ({
                    color: log.type === 'error' ? 'red' : log.type === 'success' ? 'green' : 'blue',
                    children: (
                      <div>
                        <Text type="secondary" style={{ fontSize: 12 }}>{log.time}</Text>
                        <br />
                        <Text>{log.message}</Text>
                      </div>
                    )
                  }))}
                />
              </div>
            </>
          )}

          {/* 操作按钮 */}
          <Divider />
          <div className="action-buttons">
            <Space>
              {uploadStatus.status === 'processing' && onCancel && (
                <Button onClick={onCancel}>
                  取消处理
                </Button>
              )}
              <Button onClick={fetchUploadStatus}>
                刷新状态
              </Button>
            </Space>
          </div>
        </div>
      )}

      <style jsx>{`
        .processing-status {
          max-width: 100%;
        }
        
        .file-info {
          background: #f9f9f9;
          padding: 16px;
          border-radius: 6px;
        }
        
        .process-steps {
          margin: 24px 0;
        }
        
        .processing-details {
          background: #f0f7ff;
          padding: 16px;
          border-radius: 6px;
        }
        
        .stats-row {
          margin-top: 16px;
        }
        
        .completion-results {
          background: #f6ffed;
          padding: 16px;
          border-radius: 6px;
        }
        
        .processing-logs {
          background: #fafafa;
          padding: 16px;
          border-radius: 6px;
          max-height: 200px;
          overflow-y: auto;
        }
        
        .action-buttons {
          text-align: right;
        }
        
        @media (max-width: 768px) {
          .file-info .ant-space {
            flex-direction: column;
            align-items: flex-start;
          }
          
          .stats-row .ant-space {
            flex-direction: column;
            width: 100%;
          }
          
          .completion-results .ant-space {
            flex-direction: column;
            width: 100%;
          }
        }
      `}</style>
    </Card>
  )
}

export default ProcessingStatus