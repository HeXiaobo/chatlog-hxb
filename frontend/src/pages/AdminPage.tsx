import React, { useState } from 'react'
import { Card, Row, Col, Upload, Button, message, Progress, Divider } from 'antd'
import { InboxOutlined, UploadOutlined } from '@ant-design/icons'
import type { UploadProps } from 'antd'
import api from '../services/api'

const { Dragger } = Upload

interface UploadProgress {
  status: 'uploading' | 'processing' | 'success' | 'error'
  progress: number
  message: string
  result?: {
    total_messages: number
    extracted_qa_count: number
    processing_time: number
  }
}

const AdminPage: React.FC = () => {
  const [uploading, setUploading] = useState(false)
  const [uploadProgress, setUploadProgress] = useState<UploadProgress | null>(null)

  const uploadProps: UploadProps = {
    name: 'file',
    multiple: false,
    accept: '.json',
    beforeUpload: (file) => {
      const isJSON = file.type === 'application/json' || file.name.endsWith('.json')
      if (!isJSON) {
        message.error('只能上传 JSON 文件!')
        return false
      }
      
      const isLt50M = file.size / 1024 / 1024 < 50
      if (!isLt50M) {
        message.error('文件大小不能超过 50MB!')
        return false
      }
      
      return true
    },
    customRequest: async (options) => {
      const { file, onSuccess, onError, onProgress } = options
      
      setUploading(true)
      setUploadProgress({
        status: 'uploading',
        progress: 0,
        message: '正在上传文件...'
      })

      const formData = new FormData()
      formData.append('file', file as File)

      try {
        // 上传文件
        onProgress?.({ percent: 30 })
        setUploadProgress({
          status: 'uploading',
          progress: 30,
          message: '文件上传中...'
        })

        const response = await api.post('/upload/file', formData, {
          headers: {
            'Content-Type': 'multipart/form-data'
          },
          onUploadProgress: (progressEvent) => {
            if (progressEvent.total) {
              const percent = Math.round((progressEvent.loaded * 100) / progressEvent.total)
              onProgress?.({ percent })
              setUploadProgress({
                status: 'uploading',
                progress: percent,
                message: `上传进度: ${percent}%`
              })
            }
          }
        })

        if (response.data.success) {
          // 上传成功，开始处理
          setUploadProgress({
            status: 'processing',
            progress: 100,
            message: '文件上传成功，正在处理数据...'
          })

          // 这里可以添加轮询检查处理状态的逻辑
          // 暂时模拟处理完成
          setTimeout(() => {
            setUploadProgress({
              status: 'success',
              progress: 100,
              message: '数据处理完成!',
              result: response.data.data
            })
            onSuccess?.(response.data, file as File)
            message.success('文件上传和处理完成!')
          }, 2000)

        } else {
          throw new Error(response.data.message || '上传失败')
        }

      } catch (error: any) {
        console.error('Upload error:', error)
        setUploadProgress({
          status: 'error',
          progress: 0,
          message: error.response?.data?.message || error.message || '上传失败'
        })
        onError?.(error)
        message.error('上传失败: ' + (error.response?.data?.message || error.message))
      } finally {
        setUploading(false)
      }
    },
    showUploadList: false
  }

  const resetUpload = () => {
    setUploadProgress(null)
    setUploading(false)
  }

  return (
    <div>
      <Row gutter={[24, 24]}>
        {/* 文件上传区域 */}
        <Col span={24}>
          <Card title="微信群聊数据上传" className="upload-card">
            <div style={{ textAlign: 'center', marginBottom: 24 }}>
              <h3>上传微信群聊 JSON 文件</h3>
              <p style={{ color: '#666', marginTop: 8 }}>
                请使用 chatlog 工具导出微信群聊记录，支持最大 50MB 的 JSON 文件
              </p>
            </div>

            <Dragger {...uploadProps} disabled={uploading}>
              <p className="ant-upload-drag-icon">
                <InboxOutlined />
              </p>
              <p className="ant-upload-text">
                点击或拖拽文件到此区域上传
              </p>
              <p className="ant-upload-hint">
                只支持 JSON 格式文件，文件大小不超过 50MB
              </p>
            </Dragger>

            {/* 上传进度 */}
            {uploadProgress && (
              <div style={{ marginTop: 24 }}>
                <Divider />
                <div style={{ textAlign: 'center' }}>
                  <h4>处理进度</h4>
                  <Progress 
                    percent={uploadProgress.progress}
                    status={uploadProgress.status === 'error' ? 'exception' : 'active'}
                    strokeColor={
                      uploadProgress.status === 'success' ? '#52c41a' :
                      uploadProgress.status === 'error' ? '#ff4d4f' : '#1890ff'
                    }
                  />
                  <p style={{ 
                    marginTop: 16,
                    color: uploadProgress.status === 'error' ? '#ff4d4f' : '#666'
                  }}>
                    {uploadProgress.message}
                  </p>

                  {/* 处理结果 */}
                  {uploadProgress.result && (
                    <div style={{ marginTop: 16, textAlign: 'left' }}>
                      <Card size="small">
                        <Row gutter={16}>
                          <Col span={8}>
                            <div style={{ textAlign: 'center' }}>
                              <div style={{ fontSize: '24px', color: '#1890ff' }}>
                                {uploadProgress.result.total_messages}
                              </div>
                              <div style={{ color: '#666' }}>消息总数</div>
                            </div>
                          </Col>
                          <Col span={8}>
                            <div style={{ textAlign: 'center' }}>
                              <div style={{ fontSize: '24px', color: '#52c41a' }}>
                                {uploadProgress.result.extracted_qa_count}
                              </div>
                              <div style={{ color: '#666' }}>提取问答对</div>
                            </div>
                          </Col>
                          <Col span={8}>
                            <div style={{ textAlign: 'center' }}>
                              <div style={{ fontSize: '24px', color: '#722ed1' }}>
                                {uploadProgress.result.processing_time.toFixed(1)}s
                              </div>
                              <div style={{ color: '#666' }}>处理耗时</div>
                            </div>
                          </Col>
                        </Row>
                      </Card>
                    </div>
                  )}

                  {/* 重置按钮 */}
                  {(uploadProgress.status === 'success' || uploadProgress.status === 'error') && (
                    <Button 
                      type="primary" 
                      onClick={resetUpload}
                      style={{ marginTop: 16 }}
                    >
                      继续上传
                    </Button>
                  )}
                </div>
              </div>
            )}
          </Card>
        </Col>

        {/* 使用说明 */}
        <Col span={24}>
          <Card title="使用说明">
            <div style={{ lineHeight: '1.8' }}>
              <h4>1. 准备数据</h4>
              <p style={{ marginLeft: 16, color: '#666' }}>
                使用 chatlog 工具导出微信群聊记录：
              </p>
              <div style={{ 
                marginLeft: 16, 
                padding: '12px 16px', 
                backgroundColor: '#f6f8fa',
                borderRadius: '6px',
                fontFamily: 'Monaco, Consolas, monospace',
                fontSize: '13px'
              }}>
                chatlog export --platform wechat --group-name "客户咨询群" --output wechat_data.json
              </div>

              <h4 style={{ marginTop: 24 }}>2. 上传文件</h4>
              <p style={{ marginLeft: 16, color: '#666' }}>
                将导出的 JSON 文件拖拽到上方上传区域，或点击选择文件上传
              </p>

              <h4 style={{ marginTop: 24 }}>3. 自动处理</h4>
              <p style={{ marginLeft: 16, color: '#666' }}>
                系统会自动识别并提取问答对，按照内容进行分类整理
              </p>

              <h4 style={{ marginTop: 24 }}>4. 搜索使用</h4>
              <p style={{ marginLeft: 16, color: '#666' }}>
                处理完成后即可在搜索页面查询相关问答内容
              </p>
            </div>
          </Card>
        </Col>
      </Row>
    </div>
  )
}

export default AdminPage