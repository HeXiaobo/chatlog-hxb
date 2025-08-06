import React, { useState } from 'react'
import { Upload, Button, message, Progress, Card, Alert, Steps, Typography, Space, List } from 'antd'
import { InboxOutlined, CloudUploadOutlined, CheckCircleOutlined, LoadingOutlined } from '@ant-design/icons'
import type { UploadProps, UploadFile } from 'antd'
import { supabase } from '../../lib/supabase'

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
}

const FileUploader: React.FC<FileUploaderProps> = ({
  onUploadStart,
  onUploadProgress,
  onUploadSuccess,
  onUploadError,
  maxSize = 50,
  accept = '.json',
  disabled = false
}) => {
  const [uploading, setUploading] = useState(false)
  const [processing, setProcessing] = useState(false)
  const [currentStep, setCurrentStep] = useState(0)
  const [uploadProgress, setUploadProgress] = useState(0)
  const [processingResult, setProcessingResult] = useState<ProcessingResult | null>(null)
  const [error, setError] = useState<string | null>(null)

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

      // 步骤 1: 上传文件到 Supabase Storage
      setCurrentStep(1)
      const fileName = `${Date.now()}-${file.name}`
      
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

  const steps = [
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
              </Text>
              <Progress
                percent={uploadProgress}
                status={error ? 'exception' : 'active'}
                showInfo={true}
              />
              <Text type="secondary">
                {currentStep === 1 && '上传文件到云端存储'}
                {currentStep === 2 && '验证文件格式和内容'}
                {currentStep === 3 && '解析微信消息，提取问答对'}
              </Text>
            </Space>
          </Card>
        )}

        {/* 处理结果 */}
        {processingResult && currentStep === 4 && (
          <Card type="inner" title="✅ 处理完成">
            <List size="small">
              <List.Item>
                <Text strong>原始消息数：</Text>
                <Text>{processingResult.total_messages.toLocaleString()} 条</Text>
              </List.Item>
              <List.Item>
                <Text strong>提取问答对：</Text>
                <Text type="success">{processingResult.extracted_qa_pairs.toLocaleString()} 个</Text>
              </List.Item>
              <List.Item>
                <Text strong>成功入库：</Text>
                <Text type="success">{processingResult.processed_count.toLocaleString()} 个</Text>
              </List.Item>
            </List>
            
            <div style={{ marginTop: 16 }}>
              <Space>
                <Button type="primary" onClick={() => window.location.reload()}>
                  查看知识库
                </Button>
                <Button onClick={resetUpload}>
                  继续上传
                </Button>
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