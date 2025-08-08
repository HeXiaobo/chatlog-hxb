import React, { useState, useEffect } from 'react'
import { Upload, Button, message, Progress, Card, Alert, Steps, Typography, Space, List, Switch, Tooltip, Tag, Radio } from 'antd'
import { InboxOutlined, CloudUploadOutlined, CheckCircleOutlined, LoadingOutlined, RobotOutlined, SettingOutlined, ThunderboltOutlined } from '@ant-design/icons'
import type { UploadProps, UploadFile } from 'antd'
import { supabase } from '../../lib/supabase'
import { aiService } from '../../services/aiService'

const { Dragger } = Upload
const { Text, Title } = Typography
const { Step } = Steps

interface ProcessingResult {
  upload_id: number
  total_messages: number
  extracted_qa_pairs: number
  processed_count: number
}

interface FileUploadResult {
  success: boolean
  message: string
  data?: ProcessingResult
  error?: string
}

interface FileUploaderProps {
  onUploadStart?: (file: File) => void
  onUploadProgress?: (percent: number) => void
  onUploadSuccess?: (response: any) => void
  onUploadError?: (error: Error) => void
  maxSize?: number // MB
  accept?: string
  disabled?: boolean
  defaultAIEnabled?: boolean
}

const FileUploader: React.FC<FileUploaderProps> = ({
  onUploadStart,
  onUploadProgress,
  onUploadSuccess,
  onUploadError,
  maxSize = 50,
  accept = '.json',
  disabled = false,
  defaultAIEnabled = true
}) => {
  const [uploading, setUploading] = useState(false)
  const [processing, setProcessing] = useState(false)
  const [currentStep, setCurrentStep] = useState(0)
  const [uploadProgress, setUploadProgress] = useState(0)
  const [processingResult, setProcessingResult] = useState<ProcessingResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [aiEnabled, setAiEnabled] = useState(defaultAIEnabled)
  const [aiCapabilities, setAiCapabilities] = useState<any>(null)
  const [processingMode, setProcessingMode] = useState<'standard' | 'intelligent'>('intelligent')

  // 初始化AI能力检查
  useEffect(() => {
    const loadAICapabilities = async () => {
      try {
        const capabilities = await aiService.getAICapabilities()
        setAiCapabilities(capabilities)
        if (!capabilities.ai_enabled) {
          setAiEnabled(false)
        }
      } catch (error) {
        console.error('Failed to load AI capabilities:', error)
        setAiEnabled(false)
      }
    }
    
    loadAICapabilities()
  }, [])

  const handleFileUpload = async (file: File): Promise<boolean> => {
    try {
      setError(null)
      setUploading(true)
      setCurrentStep(0)
      setUploadProgress(0)

      // 调用外部回调
      onUploadStart?.(file)

      // 验证文件
      if (!file.name.toLowerCase().endsWith(accept.replace('.', ''))) {
        throw new Error(`只支持 ${accept} 格式的文件`)
      }

      if (file.size > maxSize * 1024 * 1024) {
        throw new Error(`文件大小不能超过 ${maxSize}MB`)
      }

      // 根据处理模式选择处理方式
      if (processingMode === 'intelligent' && aiCapabilities?.ai_enabled) {
        return await handleIntelligentUpload(file)
      } else if (aiEnabled && aiCapabilities?.ai_enabled) {
        return await handleAIUpload(file)
      } else {
        return await handleTraditionalUpload(file)
      }

    } catch (error: any) {
      console.error('文件上传处理失败:', error)
      const errorObj = new Error(error.message || '文件处理失败')
      setError(errorObj.message)
      setUploading(false)
      setProcessing(false)
      setCurrentStep(0)
      message.error(errorObj.message)
      
      // 调用错误回调
      onUploadError?.(errorObj)
      
      return false
    }
  }

  const handleIntelligentUpload = async (file: File): Promise<boolean> => {
    try {
      // 步骤 1: 智能分析与处理
      setCurrentStep(1)
      setProcessing(true)
      setUploading(false)
      
      const result = await aiService.uploadFileWithIntelligentProcessing(file, (progress) => {
        setUploadProgress(progress)
        onUploadProgress?.(progress)
      })
      
      // 步骤 4: 处理完成
      setCurrentStep(4)
      setProcessingResult({
        upload_id: result.upload_id,
        total_messages: result.processing_summary?.original_messages || 0,
        extracted_qa_pairs: result.processing_summary?.qa_pairs_extracted || 0,
        processed_count: result.processing_summary?.final_knowledge_entries || 0
      })
      setProcessing(false)
      setUploadProgress(100)
      onUploadProgress?.(100)
      
      const summary = result.processing_summary
      message.success(
        `🤖 智能处理完成! 从 ${summary?.original_messages || 0} 条消息中生成 ${summary?.final_knowledge_entries || 0} 个高质量知识库条目`
      )
      
      onUploadSuccess?.(result)
      return true
      
    } catch (error: any) {
      throw error
    }
  }

  const handleAIUpload = async (file: File): Promise<boolean> => {
    try {
      // 步骤 1: 使用AI处理文件
      setCurrentStep(1)
      setProcessing(true)
      setUploading(false)

      const result = await aiService.uploadFileWithAI(file, (progress) => {
        setUploadProgress(progress)
        onUploadProgress?.(progress)
      })

      // 步骤 4: 处理完成
      setCurrentStep(4)
      setProcessingResult({
        upload_id: result.upload_id,
        total_messages: 0, // AI处理结果没有这个字段
        extracted_qa_pairs: result.total_extracted,
        processed_count: result.total_saved
      })
      setProcessing(false)
      setUploadProgress(100)
      onUploadProgress?.(100)

      message.success(`AI处理完成！提取了 ${result.total_extracted} 个问答对，保存了 ${result.total_saved} 个`)
      
      // 调用成功回调
      onUploadSuccess?.(result)
      
      return true

    } catch (error: any) {
      throw error
    }
  }

  const handleTraditionalUpload = async (file: File): Promise<boolean> => {
    try {
      // 步骤 1: 上传文件到 Supabase Storage
      setCurrentStep(1)
      
      // 自动处理中文文件名，转换为英文以避免编码问题
      const sanitizedFileName = file.name
        .replace(/[\u4e00-\u9fff]/g, '') // 移除中文字符
        .replace(/[^\w\-_\.]/g, '_') // 替换特殊字符为下划线
        .replace(/_{2,}/g, '_') // 合并多个下划线
        .replace(/^_+|_+$/g, '') // 移除首尾下划线
        .replace(/\.{2,}/g, '.') // 合并多个点
        .toLowerCase()
      
      const finalFileName = sanitizedFileName || `wechat_export_${Date.now()}.json`
      const fileName = `${Date.now()}-${finalFileName}`
      
      const { error: uploadError } = await supabase.storage
        .from('wechat-files')
        .upload(fileName, file, {
          cacheControl: '3600',
          upsert: false
        })

      if (uploadError) {
        throw new Error(`文件上传失败: ${uploadError.message}`)
      }

      setUploadProgress(50)
      onUploadProgress?.(50)

      // 步骤 2: 读取文件内容
      setCurrentStep(2)
      const fileContent = await readFileContent(file)
      setUploadProgress(75)
      onUploadProgress?.(75)

      // 步骤 3: 调用 Edge Function 处理文件
      setCurrentStep(3)
      setProcessing(true)
      setUploading(false)

      const { data, error: functionError } = await supabase.functions.invoke('process-wechat-file', {
        body: {
          fileName: file.name,
          fileContent: fileContent
        }
      })

      if (functionError) {
        throw new Error(`处理失败: ${functionError.message}`)
      }

      const result = data as FileUploadResult
      
      if (!result.success) {
        throw new Error(result.error || '文件处理失败')
      }

      // 步骤 4: 处理完成
      setCurrentStep(4)
      setProcessingResult(result.data || null)
      setProcessing(false)
      setUploadProgress(100)
      onUploadProgress?.(100)

      message.success(`成功处理文件！提取了 ${result.data?.extracted_qa_pairs || 0} 个问答对`)
      
      // 调用成功回调
      onUploadSuccess?.(result)
      
      return true

    } catch (error: any) {
      throw error
    }
  }

  const readFileContent = (file: File): Promise<any> => {
    return new Promise((resolve, reject) => {
      const reader = new FileReader()
      
      reader.onload = (e) => {
        try {
          const content = e.target?.result as string
          const jsonData = JSON.parse(content)
          resolve(jsonData)
        } catch (error) {
          reject(new Error('JSON 文件格式无效'))
        }
      }
      
      reader.onerror = () => {
        reject(new Error('文件读取失败'))
      }
      
      reader.readAsText(file, 'UTF-8')
    })
  }

  const uploadProps: UploadProps = {
    name: 'file',
    multiple: false,
    accept: accept,
    disabled: disabled || uploading || processing,
    beforeUpload: (file) => {
      handleFileUpload(file)
      return false // 阻止默认上传行为
    },
    showUploadList: false
  }

  const resetUpload = () => {
    setCurrentStep(0)
    setUploadProgress(0)
    setProcessingResult(null)
    setError(null)
    setUploading(false)
    setProcessing(false)
  }

  const getSteps = () => {
    if (processingMode === 'intelligent' && aiCapabilities?.ai_enabled) {
      // 智能处理流程
      return [
        {
          title: '选择文件',
          description: '选择微信聊天记录 JSON 文件',
          icon: <InboxOutlined />
        },
        {
          title: '智能分析',
          description: 'AI深度分析聊天内容，筛选有价值信息',
          icon: processing ? <LoadingOutlined /> : <ThunderboltOutlined />
        },
        {
          title: '内容清洗',
          description: 'AI优化问答质量，生成结构化知识',
          icon: processing ? <LoadingOutlined /> : <RobotOutlined />
        },
        {
          title: '入库保存',
          description: '保存高质量知识库条目',
          icon: processing ? <LoadingOutlined /> : <CheckCircleOutlined />
        },
        {
          title: '完成',
          description: '智能处理完成',
          icon: <CheckCircleOutlined />
        }
      ]
    } else if (aiEnabled && aiCapabilities?.ai_enabled) {
      // 标准AI处理流程
      return [
        {
          title: '选择文件',
          description: '选择微信聊天记录 JSON 文件',
          icon: <InboxOutlined />
        },
        {
          title: 'AI智能处理',
          description: '使用AI大模型智能提取问答对',
          icon: processing ? <LoadingOutlined /> : <RobotOutlined />
        },
        {
          title: '智能分类',
          description: 'AI自动分类和质量评估',
          icon: processing ? <LoadingOutlined /> : <CheckCircleOutlined />
        },
        {
          title: '数据入库',
          description: '保存到知识库',
          icon: processing ? <LoadingOutlined /> : <CheckCircleOutlined />
        },
        {
          title: '完成',
          description: '数据已添加到知识库',
          icon: <CheckCircleOutlined />
        }
      ]
    } else {
      // 传统处理流程
      return [
        {
          title: '选择文件',
          description: '选择微信聊天记录 JSON 文件',
          icon: <InboxOutlined />
        },
        {
          title: '上传文件',
          description: '将文件上传到云端存储',
          icon: uploading ? <LoadingOutlined /> : <CloudUploadOutlined />
        },
        {
          title: '验证格式',
          description: '验证文件格式和内容',
          icon: processing ? <LoadingOutlined /> : <CheckCircleOutlined />
        },
        {
          title: '解析数据',
          description: '提取问答对并自动分类',
          icon: processing ? <LoadingOutlined /> : <CheckCircleOutlined />
        },
        {
          title: '完成',
          description: '数据已添加到知识库',
          icon: <CheckCircleOutlined />
        }
      ]
    }
  }

  const steps = getSteps()

  return (
    <Card>
      <Space direction="vertical" style={{ width: '100%' }} size="large">
        {/* 步骤指示器 */}
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

        {/* 错误提示 */}
        {error && (
          <Alert
            message="处理失败"
            description={error}
            type="error"
            showIcon
            closable
            onClose={() => setError(null)}
          />
        )}

        {/* 处理模式选择 */}
        {currentStep <= 1 && aiCapabilities && aiCapabilities.ai_enabled && (
          <Card type="inner" title="⚙️ 处理模式选择">
            <Space direction="vertical" style={{ width: '100%' }}>
              <Radio.Group 
                value={processingMode} 
                onChange={(e) => setProcessingMode(e.target.value)}
                style={{ width: '100%' }}
              >
                <Space direction="vertical" style={{ width: '100%' }}>
                  <Radio value="intelligent">
                    <Space>
                      <ThunderboltOutlined style={{ color: '#722ed1' }} />
                      <Text strong>智能处理模式</Text>
                      <Tag color="purple">推荐</Tag>
                    </Space>
                    <div style={{ marginLeft: 24, marginTop: 4 }}>
                      <Text type="secondary" style={{ fontSize: '12px' }}>
                        AI智能分析 → 筛选有价值内容 → 提取问答对 → 内容清洗优化 → 生成高质量知识库
                      </Text>
                    </div>
                  </Radio>
                  <Radio value="standard">
                    <Space>
                      <RobotOutlined style={{ color: '#1890ff' }} />
                      <Text strong>标准AI处理</Text>
                    </Space>
                    <div style={{ marginLeft: 24, marginTop: 4 }}>
                      <Text type="secondary" style={{ fontSize: '12px' }}>
                        基础AI提取问答对 + 自动分类（兼容性更好，处理速度快）
                      </Text>
                    </div>
                  </Radio>
                </Space>
              </Radio.Group>
            </Space>
          </Card>
        )}

        {/* AI处理选项 */}
        {currentStep <= 1 && aiCapabilities && processingMode === 'standard' && (
          <Card type="inner" title="🤖 AI处理设置">
            <Space direction="vertical" style={{ width: '100%' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <Space>
                  <RobotOutlined style={{ color: aiEnabled ? '#52c41a' : '#d9d9d9' }} />
                  <Text strong>AI智能提取</Text>
                  <Tooltip title={
                    aiCapabilities.ai_enabled 
                      ? "使用AI大模型智能提取问答对，提高数据质量"
                      : "AI功能暂不可用，将使用传统规则提取"
                  }>
                    <Tag color={aiCapabilities.ai_enabled ? 'success' : 'warning'}>
                      {aiCapabilities.ai_enabled ? '可用' : '不可用'}
                    </Tag>
                  </Tooltip>
                </Space>
                <Switch 
                  checked={aiEnabled}
                  disabled={!aiCapabilities.ai_enabled}
                  onChange={setAiEnabled}
                />
              </div>
              
              {aiEnabled && aiCapabilities.ai_enabled && (
                <div style={{ paddingLeft: 24 }}>
                  <Text type="secondary" style={{ fontSize: '12px' }}>
                    • 主要提供商: {aiCapabilities.primary_provider || '未配置'}<br/>
                    • 今日已用: {aiCapabilities.usage_stats?.daily_requests || 0} 次请求<br/>
                    • 成功率: {((aiCapabilities.usage_stats?.success_rate || 0) * 100).toFixed(1)}%
                  </Text>
                </div>
              )}

              {!aiCapabilities.ai_enabled && (
                <Alert
                  message="AI功能未启用"
                  description="将使用传统规则进行数据提取。如需启用AI功能，请联系管理员配置。"
                  type="info"
                  showIcon
                  style={{ marginTop: 8 }}
                />
              )}
            </Space>
          </Card>
        )}

        {/* 上传区域 */}
        {currentStep <= 1 && (
          <Card type="inner">
            <Dragger {...uploadProps} disabled={uploading || processing}>
              <p className="ant-upload-drag-icon">
                <InboxOutlined style={{ fontSize: '48px', color: '#1890ff' }} />
              </p>
              <p className="ant-upload-text">点击或拖拽文件到此区域上传</p>
              <p className="ant-upload-hint">
                支持微信聊天记录导出的 JSON 文件，文件大小不超过 {maxSize}MB
                {processingMode === 'intelligent' && aiCapabilities?.ai_enabled
                  ? ' (将使用AI智能深度处理)'
                  : aiEnabled && aiCapabilities?.ai_enabled
                  ? ' (将使用标准AI提取)'
                  : ' (将使用规则提取)'
                }
              </p>
            </Dragger>
          </Card>
        )}

        {/* 处理进度 */}
        {(uploading || processing) && (
          <Card type="inner">
            <Space direction="vertical" style={{ width: '100%' }}>
              <Text strong>
                {uploading ? '正在上传文件...' : '正在处理数据...'}
                {processingMode === 'intelligent' && aiCapabilities?.ai_enabled && processing && ' (智能深度处理中)'}
                {processingMode === 'standard' && aiEnabled && aiCapabilities?.ai_enabled && processing && ' (AI智能处理中)'}
              </Text>
              <Progress
                percent={uploadProgress}
                status={error ? 'exception' : 'active'}
                showInfo={true}
              />
              <Text type="secondary">
                {processingMode === 'intelligent' && aiCapabilities?.ai_enabled ? (
                  // 智能处理流程的提示
                  <>
                    {currentStep === 1 && (
                      <Space>
                        <ThunderboltOutlined style={{ color: '#722ed1' }} />
                        AI深度分析聊天内容，筛选有价值信息
                      </Space>
                    )}
                    {currentStep === 2 && (
                      <Space>
                        <RobotOutlined style={{ color: '#1890ff' }} />
                        AI优化问答质量，内容清洗与结构化
                      </Space>
                    )}
                    {currentStep === 3 && '保存高质量知识库条目'}
                  </>
                ) : aiEnabled && aiCapabilities?.ai_enabled ? (
                  // 标准AI处理流程的提示
                  <>
                    {currentStep === 1 && (
                      <Space>
                        <RobotOutlined style={{ color: '#1890ff' }} />
                        AI智能分析聊天记录，提取问答对
                      </Space>
                    )}
                    {currentStep === 2 && '智能分类和质量评估'}
                    {currentStep === 3 && '保存到知识库'}
                  </>
                ) : (
                  // 传统处理流程的提示
                  <>
                    {currentStep === 1 && '上传文件到云端存储'}
                    {currentStep === 2 && '验证文件格式和内容'}
                    {currentStep === 3 && '解析微信消息，提取问答对'}
                  </>
                )}
              </Text>
            </Space>
          </Card>
        )}

        {/* 处理结果 */}
        {processingResult && currentStep === 4 && (
          <Card type="inner" title={
            <Space>
              {aiEnabled && aiCapabilities?.ai_enabled ? (
                <>
                  <RobotOutlined style={{ color: '#52c41a' }} />
                  AI智能处理完成
                </>
              ) : (
                <>✅ 处理完成</>
              )}
            </Space>
          }>
            <List size="small">
              {!aiEnabled && processingResult.total_messages > 0 && (
                <List.Item>
                  <Text strong>原始消息数：</Text>
                  <Text>{processingResult.total_messages.toLocaleString()} 条</Text>
                </List.Item>
              )}
              <List.Item>
                <Text strong>{aiEnabled && aiCapabilities?.ai_enabled ? 'AI提取问答对：' : '提取问答对：'}</Text>
                <Text type="success">{processingResult.extracted_qa_pairs.toLocaleString()} 个</Text>
              </List.Item>
              <List.Item>
                <Text strong>成功入库：</Text>
                <Text type="success">{processingResult.processed_count.toLocaleString()} 个</Text>
              </List.Item>
              {aiEnabled && aiCapabilities?.ai_enabled && (
                <List.Item>
                  <Text strong>处理方式：</Text>
                  <Tag color="blue" icon={<RobotOutlined />}>AI智能处理</Tag>
                </List.Item>
              )}
            </List>
            
            <div style={{ marginTop: 16 }}>
              <Space>
                <Button type="primary" onClick={() => window.location.reload()}>
                  查看知识库
                </Button>
                <Button onClick={resetUpload}>
                  继续上传
                </Button>
                {aiEnabled && aiCapabilities?.ai_enabled && (
                  <Button type="link" onClick={() => window.open('/ai', '_blank')}>
                    查看AI统计
                  </Button>
                )}
              </Space>
            </div>
          </Card>
        )}

        {/* 文件格式说明 */}
        <Card type="inner" title="📝 文件格式说明" size="small">
          <Text type="secondary">
            <p>支持的微信聊天记录 JSON 格式：</p>
            <ul>
              <li>使用 chatlog 工具导出的标准格式</li>
              <li>包含消息内容、发送者、时间戳等信息</li>
              <li>系统会自动识别问答模式并提取有价值的对话</li>
              <li>自动分类到：产品咨询、技术支持、价格费用、使用教程、售后问题</li>
            </ul>
          </Text>
        </Card>
      </Space>
    </Card>
  )
}

export default FileUploader