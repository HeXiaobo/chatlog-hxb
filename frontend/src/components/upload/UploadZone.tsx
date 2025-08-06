import React, { useState, useCallback } from 'react'
import { Upload, Button, message, Progress, Alert, Space, Typography } from 'antd'
import { InboxOutlined, FileTextOutlined, CloudUploadOutlined } from '@ant-design/icons'
import type { UploadResponse, APIResponse } from '../../types'
import api from '../../services/api'

const { Dragger } = Upload
const { Text, Title } = Typography

interface UploadZoneProps {
  onUploadStart?: (file: File) => void
  onUploadProgress?: (percent: number) => void
  onUploadSuccess?: (response: UploadResponse) => void
  onUploadError?: (error: Error) => void
  maxSize?: number // MB
  accept?: string
  disabled?: boolean
}

interface UploadState {
  uploading: boolean
  progress: number
  error: string | null
  success: boolean
  result: UploadResponse | null
}

const UploadZone: React.FC<UploadZoneProps> = ({
  onUploadStart,
  onUploadProgress,
  onUploadSuccess,
  onUploadError,
  maxSize = 50,
  accept = '.json',
  disabled = false
}) => {
  const [uploadState, setUploadState] = useState<UploadState>({
    uploading: false,
    progress: 0,
    error: null,
    success: false,
    result: null
  })

  const resetUploadState = useCallback(() => {
    setUploadState({
      uploading: false,
      progress: 0,
      error: null,
      success: false,
      result: null
    })
  }, [])

  const validateFile = useCallback((file: File): boolean => {
    // 检查文件类型
    if (!file.name.toLowerCase().endsWith('.json')) {
      message.error('只支持 JSON 格式的文件')
      return false
    }

    // 检查文件大小
    const fileSizeMB = file.size / (1024 * 1024)
    if (fileSizeMB > maxSize) {
      message.error(`文件大小不能超过 ${maxSize}MB`)
      return false
    }

    // 检查文件内容（基本验证）
    return true
  }, [maxSize])

  const uploadFile = useCallback(async (file: File) => {
    if (!validateFile(file)) {
      return false
    }

    setUploadState(prev => ({ ...prev, uploading: true, progress: 0, error: null }))
    onUploadStart?.(file)

    const formData = new FormData()
    formData.append('file', file)

    try {
      const response = await api.post<APIResponse<UploadResponse>>('/upload/file', formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        },
        onUploadProgress: (progressEvent) => {
          if (progressEvent.total) {
            const percent = Math.round((progressEvent.loaded * 100) / progressEvent.total)
            setUploadState(prev => ({ ...prev, progress: percent }))
            onUploadProgress?.(percent)
          }
        }
      })

      if (response.data.success && response.data.data) {
        setUploadState(prev => ({
          ...prev,
          uploading: false,
          success: true,
          result: response.data.data
        }))
        onUploadSuccess?.(response.data.data)
        message.success('文件上传并处理完成！')
      } else {
        throw new Error(response.data.error?.message || '上传失败')
      }
    } catch (error: any) {
      const errorMsg = error.response?.data?.error?.message || error.message || '上传失败'
      setUploadState(prev => ({
        ...prev,
        uploading: false,
        error: errorMsg
      }))
      onUploadError?.(error)
      message.error(errorMsg)
    }

    return false // 阻止默认上传行为
  }, [validateFile, onUploadStart, onUploadProgress, onUploadSuccess, onUploadError])

  const draggerProps = {
    name: 'file',
    multiple: false,
    accept,
    disabled: disabled || uploadState.uploading,
    beforeUpload: uploadFile,
    showUploadList: false
  }

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 B'
    const k = 1024
    const sizes = ['B', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
  }

  return (
    <div className="upload-zone">
      {!uploadState.success ? (
        <Dragger {...draggerProps} className={uploadState.uploading ? 'uploading' : ''}>
          <div className="ant-upload-drag-icon">
            {uploadState.uploading ? (
              <CloudUploadOutlined style={{ color: '#1890ff' }} />
            ) : (
              <InboxOutlined />
            )}
          </div>
          <p className="ant-upload-text">
            {uploadState.uploading ? '正在上传处理...' : '点击或拖拽文件到此区域上传'}
          </p>
          <p className="ant-upload-hint">
            {uploadState.uploading
              ? `处理中，请稍候...`
              : `支持 JSON 格式的微信聊天记录文件，文件大小不超过 ${maxSize}MB`
            }
          </p>
          
          {uploadState.uploading && (
            <div style={{ marginTop: 16, maxWidth: 300, margin: '16px auto 0' }}>
              <Progress 
                percent={uploadState.progress} 
                size="small"
                status={uploadState.progress === 100 ? 'success' : 'active'}
              />
            </div>
          )}
        </Dragger>
      ) : (
        <div style={{ textAlign: 'center', padding: '40px 20px' }}>
          <FileTextOutlined style={{ fontSize: 48, color: '#52c41a', marginBottom: 16 }} />
          <Title level={4} style={{ color: '#52c41a', marginBottom: 16 }}>
            上传成功！
          </Title>
          
          {uploadState.result && (
            <Space direction="vertical" size="small" style={{ marginBottom: 24 }}>
              <Text strong>处理结果：</Text>
              <div>
                <Text>文件名：{uploadState.result.filename}</Text>
              </div>
              <div>
                <Text>消息总数：{uploadState.result.total_messages}</Text>
              </div>
              <div>
                <Text>提取问答：{uploadState.result.extracted_qa_count} 条</Text>
              </div>
              <div>
                <Text>处理耗时：{uploadState.result.processing_time.toFixed(2)}s</Text>
              </div>
            </Space>
          )}
          
          <Button type="primary" onClick={resetUploadState}>
            继续上传
          </Button>
        </div>
      )}

      {uploadState.error && (
        <Alert
          message="上传失败"
          description={uploadState.error}
          type="error"
          showIcon
          style={{ marginTop: 16 }}
          action={
            <Button size="small" onClick={resetUploadState}>
              重试
            </Button>
          }
        />
      )}

      <style jsx>{`
        .upload-zone .uploading {
          border-color: #1890ff;
          background-color: #f0f7ff;
        }
        
        .upload-zone .ant-upload-drag:hover {
          border-color: #40a9ff;
        }
        
        .upload-zone .ant-upload-drag.ant-upload-drag-hover {
          border-color: #1890ff;
          background-color: #f0f7ff;
        }
      `}</style>
    </div>
  )
}

export default UploadZone