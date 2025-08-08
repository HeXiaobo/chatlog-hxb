import React, { useState, useEffect } from 'react'
import { Card, Row, Col, Button, Space, Alert, message, Steps, Typography, Statistic } from 'antd'
import { MessageOutlined, CloudDownloadOutlined, CheckCircleOutlined, LoadingOutlined, ExclamationCircleOutlined } from '@ant-design/icons'
import QueryForm from '../components/chatlog/QueryForm'
import MessageList from '../components/chatlog/MessageList'
import { chatlogService } from '../services/chatlogService'
import type { ChatlogMessage, QueryParams, ImportResult } from '../types/chatlog'

const { Title, Text } = Typography
const { Step } = Steps

interface ImportStats {
  queried: number
  selected: number
  imported: number
  processed: number
}

const ChatlogImportPage: React.FC = () => {
  const [loading, setLoading] = useState(false)
  const [importing, setImporting] = useState(false)
  const [messages, setMessages] = useState<ChatlogMessage[]>([])
  const [selectedMessages, setSelectedMessages] = useState<ChatlogMessage[]>([])
  const [currentStep, setCurrentStep] = useState(0)
  const [importStats, setImportStats] = useState<ImportStats>({
    queried: 0,
    selected: 0,
    imported: 0,
    processed: 0
  })
  const [apiError, setApiError] = useState<string | null>(null)
  const [importResult, setImportResult] = useState<ImportResult | null>(null)

  // 检查chatlog服务状态
  const checkChatlogService = async () => {
    try {
      const isAvailable = await chatlogService.checkServiceStatus()
      if (!isAvailable) {
        setApiError('Chatlog服务未运行。请先启动chatlog工具并确保API服务在 http://127.0.0.1:5030 上运行。')
      }
      return isAvailable
    } catch (error) {
      setApiError('无法连接到Chatlog服务。请检查chatlog工具是否正常运行。')
      return false
    }
  }

  useEffect(() => {
    checkChatlogService()
  }, [])

  // 处理查询聊天记录
  const handleQuery = async (params: QueryParams) => {
    setLoading(true)
    setApiError(null)
    setCurrentStep(1)
    
    try {
      const result = await chatlogService.queryChatlog(params)
      setMessages(result)
      setImportStats(prev => ({
        ...prev,
        queried: result.length,
        selected: 0
      }))
      setCurrentStep(2)
      message.success(`成功查询到 ${result.length} 条聊天记录`)
    } catch (error: any) {
      console.error('Query failed:', error)
      setApiError(`查询失败: ${error.message || '未知错误'}`)
      setCurrentStep(0)
    } finally {
      setLoading(false)
    }
  }

  // 处理消息选择
  const handleMessageSelection = (selected: ChatlogMessage[]) => {
    setSelectedMessages(selected)
    setImportStats(prev => ({
      ...prev,
      selected: selected.length
    }))
  }

  // 处理导入到知识库
  const handleImport = async () => {
    if (selectedMessages.length === 0) {
      message.warning('请先选择要导入的聊天记录')
      return
    }

    setImporting(true)
    setCurrentStep(3)
    
    try {
      const result = await chatlogService.importToKnowledgeBase(selectedMessages)
      
      setImportResult(result)
      setImportStats(prev => ({
        ...prev,
        imported: selectedMessages.length,
        processed: result.total_saved
      }))
      setCurrentStep(4)
      
      message.success(`成功导入 ${result.total_saved} 个问答对到知识库`)
    } catch (error: any) {
      console.error('Import failed:', error)
      setApiError(`导入失败: ${error.message || '未知错误'}`)
      message.error('导入失败，请重试')
    } finally {
      setImporting(false)
    }
  }

  // 重置所有状态
  const handleReset = () => {
    setMessages([])
    setSelectedMessages([])
    setCurrentStep(0)
    setImportStats({
      queried: 0,
      selected: 0,
      imported: 0,
      processed: 0
    })
    setApiError(null)
    setImportResult(null)
  }

  const steps = [
    {
      title: '设置查询条件',
      description: '选择时间范围和群聊',
      icon: <MessageOutlined />
    },
    {
      title: '查询聊天记录',
      description: '从微信数据库获取记录',
      icon: loading ? <LoadingOutlined /> : <CloudDownloadOutlined />
    },
    {
      title: '选择导入内容',
      description: '预览并选择要导入的消息',
      icon: <MessageOutlined />
    },
    {
      title: '导入到知识库',
      description: '处理并保存到知识库',
      icon: importing ? <LoadingOutlined /> : <CloudDownloadOutlined />
    },
    {
      title: '完成',
      description: '导入完成，查看结果',
      icon: <CheckCircleOutlined />
    }
  ]

  return (
    <div style={{ padding: '24px' }}>
      <Card style={{ marginBottom: 24 }}>
        <Title level={2} style={{ marginBottom: 8 }}>
          📱 微信聊天记录导入
        </Title>
        <Text type="secondary">
          直接从微信聊天记录中查询、预览并导入问答对到知识库
        </Text>
      </Card>

      {/* API 错误提示 */}
      {apiError && (
        <Alert
          message="服务连接问题"
          description={apiError}
          type="error"
          icon={<ExclamationCircleOutlined />}
          showIcon
          closable
          style={{ marginBottom: 24 }}
          onClose={() => setApiError(null)}
          action={
            <Button size="small" onClick={checkChatlogService}>
              重新检测
            </Button>
          }
        />
      )}

      {/* 步骤指示器 */}
      <Card style={{ marginBottom: 24 }}>
        <Steps current={currentStep} size="small">
          {steps.map((step, index) => (
            <Step
              key={index}
              title={step.title}
              description={step.description}
              icon={step.icon}
            />
          ))}
        </Steps>
      </Card>

      {/* 统计数据 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={12} sm={6}>
          <Card>
            <Statistic
              title="已查询"
              value={importStats.queried}
              suffix="条"
              loading={loading}
            />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card>
            <Statistic
              title="已选择"
              value={importStats.selected}
              suffix="条"
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card>
            <Statistic
              title="已导入"
              value={importStats.imported}
              suffix="条"
              valueStyle={{ color: '#52c41a' }}
              loading={importing}
            />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card>
            <Statistic
              title="已处理"
              value={importStats.processed}
              suffix="个问答"
              valueStyle={{ color: '#722ed1' }}
              loading={importing}
            />
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]}>
        {/* 查询表单 */}
        <Col xs={24} lg={8}>
          <Card title="查询条件" style={{ height: '100%' }}>
            <QueryForm
              onQuery={handleQuery}
              loading={loading}
              disabled={importing}
            />
            
            {currentStep >= 2 && (
              <div style={{ marginTop: 16, paddingTop: 16, borderTop: '1px solid #f0f0f0' }}>
                <Space direction="vertical" style={{ width: '100%' }}>
                  <Button 
                    type="primary" 
                    onClick={handleImport}
                    loading={importing}
                    disabled={selectedMessages.length === 0 || importing}
                    block
                  >
                    导入到知识库 ({selectedMessages.length}条)
                  </Button>
                  <Button onClick={handleReset} disabled={loading || importing} block>
                    重新开始
                  </Button>
                </Space>
              </div>
            )}
          </Card>
        </Col>

        {/* 消息列表和结果展示 */}
        <Col xs={24} lg={16}>
          {currentStep >= 2 && currentStep < 4 && (
            <Card title={`聊天记录 (${messages.length}条)`} style={{ height: '100%' }}>
              <MessageList
                messages={messages}
                selectedMessages={selectedMessages}
                onSelectionChange={handleMessageSelection}
                loading={loading}
              />
            </Card>
          )}

          {currentStep === 4 && importResult && (
            <Card title="✅ 导入完成" style={{ height: '100%' }}>
              <div style={{ textAlign: 'center', padding: '20px 0' }}>
                <CheckCircleOutlined style={{ fontSize: '64px', color: '#52c41a', marginBottom: 16 }} />
                <Title level={3}>导入成功！</Title>
                <Text type="secondary">已成功将聊天记录导入到知识库</Text>
              </div>

              <Row gutter={[16, 16]} style={{ marginTop: 24 }}>
                <Col span={12}>
                  <Card size="small">
                    <Statistic
                      title="处理消息"
                      value={importResult.total_extracted}
                      suffix="条"
                    />
                  </Card>
                </Col>
                <Col span={12}>
                  <Card size="small">
                    <Statistic
                      title="生成问答对"
                      value={importResult.total_saved}
                      suffix="个"
                      valueStyle={{ color: '#52c41a' }}
                    />
                  </Card>
                </Col>
              </Row>

              {importResult.statistics && (
                <div style={{ marginTop: 16, padding: 16, background: '#fafafa', borderRadius: 6 }}>
                  <Text strong>处理详情：</Text>
                  <ul style={{ marginTop: 8, marginBottom: 0 }}>
                    <li>处理时间: {importResult.processing_time?.toFixed(2)}秒</li>
                    <li>文件来源: 微信聊天记录导入</li>
                    {importResult.statistics.extraction && (
                      <li>提取效率: {((importResult.total_saved / importResult.total_extracted) * 100).toFixed(1)}%</li>
                    )}
                  </ul>
                </div>
              )}

              <div style={{ textAlign: 'center', marginTop: 24 }}>
                <Space>
                  <Button type="primary" onClick={() => {
                    // 如果有生成问答对，跳转到搜索页面显示最新记录
                    // 如果没有生成问答对，跳转到首页查看统计信息
                    if (importResult.total_saved > 0) {
                      window.location.href = '/search?q=&sort=time'
                    } else {
                      window.location.href = '/'
                    }
                  }}>
                    {importResult.total_saved > 0 ? '查看新增问答' : '返回首页'}
                  </Button>
                  <Button onClick={handleReset}>
                    继续导入
                  </Button>
                </Space>
              </div>
            </Card>
          )}

          {currentStep < 2 && (
            <Card title="📝 使用说明" style={{ height: '100%' }}>
              <div style={{ padding: '20px 0' }}>
                <Title level={4}>如何使用？</Title>
                <ol style={{ lineHeight: '2' }}>
                  <li><strong>启动chatlog服务</strong>：确保chatlog工具正在运行并监听端口5030</li>
                  <li><strong>设置查询条件</strong>：选择时间范围、群聊和其他筛选条件</li>
                  <li><strong>查询聊天记录</strong>：系统自动从微信数据库获取符合条件的记录</li>
                  <li><strong>预览和选择</strong>：浏览查询结果，选择要导入的有价值内容</li>
                  <li><strong>一键导入</strong>：系统自动提取问答对并保存到知识库</li>
                </ol>

                <Alert
                  message="提示"
                  description="请确保chatlog工具正在运行，否则无法查询聊天记录。建议先在小范围时间内测试功能。"
                  type="info"
                  showIcon
                  style={{ marginTop: 16 }}
                />
              </div>
            </Card>
          )}
        </Col>
      </Row>
    </div>
  )
}

export default ChatlogImportPage