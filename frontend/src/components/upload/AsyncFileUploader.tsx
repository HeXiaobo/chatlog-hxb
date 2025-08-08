/**
 * 异步文件上传组件 - 支持后台任务队列和实时状态更新
 */
import React, { useState, useRef, useCallback } from 'react'
import {
  Upload,
  Button,
  Card,
  Progress,
  Alert,
  Tag,
  Space,
  Typography,
  List,
  Collapse,
  Select,
  Switch,
  Tooltip,
  notification
} from 'antd'
import {
  UploadOutlined,
  CloudUploadOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  ClockCircleOutlined,
  StopOutlined,
  ReloadOutlined,
  InfoCircleOutlined
} from '@ant-design/icons'
import { UploadFile, RcFile } from 'antd/es/upload'
import { useTaskStatus } from '../../hooks/useWebSocket'
import { uploadFileAsync, cancelTask } from '../../services/api'

const { Title, Text, Paragraph } = Typography
const { Panel } = Collapse
const { Option } = Select

interface AsyncUploadTask {
  taskId: string
  filename: string
  uploadTime: Date
  priority: string
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled'
}

interface AsyncFileUploaderProps {
  onUploadComplete?: (result: any) => void
  onUploadError?: (error: any) => void
  maxFileSize?: number // MB
  allowedExtensions?: string[]
  showAdvancedOptions?: boolean
}

const AsyncFileUploader: React.FC<AsyncFileUploaderProps> = ({
  onUploadComplete,
  onUploadError,
  maxFileSize = 50,
  allowedExtensions = ['.json'],
  showAdvancedOptions = false
}) => {
  const [fileList, setFileList] = useState<UploadFile[]>([])
  const [uploading, setUploading] = useState(false)
  const [priority, setPriority] = useState<'low' | 'normal' | 'high' | 'urgent'>('normal')
  const [autoRefresh, setAutoRefresh] = useState(true)
  const [uploadTasks, setUploadTasks] = useState<AsyncUploadTask[]>([])
  
  const uploadRef = useRef<any>(null)

  // 任务状态监听
  const currentTaskId = uploadTasks.find(task => task.status === 'running')?.taskId || null
  const { taskStatus, isLoading, isCompleted, isFailed, error, result, clearStatus } = useTaskStatus(currentTaskId)

  // 文件验证
  const beforeUpload = useCallback((file: RcFile) => {
    // 检查文件大小
    const fileSizeMB = file.size / 1024 / 1024
    if (fileSizeMB > maxFileSize) {
      notification.error({
        message: '文件过大',
        description: `文件大小不能超过 ${maxFileSize}MB`
      })
      return false
    }

    // 检查文件类型
    const extension = `.${file.name.split('.').pop()?.toLowerCase()}`
    if (!allowedExtensions.includes(extension)) {
      notification.error({
        message: '文件类型不支持',
        description: `仅支持以下格式：${allowedExtensions.join(', ')}`
      })
      return false
    }

    return true
  }, [maxFileSize, allowedExtensions])

  // 处理文件上传
  const handleUpload = useCallback(async () => {
    if (fileList.length === 0) {
      notification.warning({
        message: '请选择文件',
        description: '请先选择要上传的文件'
      })
      return
    }

    const file = fileList[0]
    if (!file.originFileObj) return

    setUploading(true)

    try {
      const formData = new FormData()
      formData.append('file', file.originFileObj)
      formData.append('priority', priority)

      const response = await uploadFileAsync(formData)
      
      if (response.success) {
        const newTask: AsyncUploadTask = {
          taskId: response.data.task_id,
          filename: response.data.filename,
          uploadTime: new Date(),
          priority: priority,
          status: 'pending'
        }

        setUploadTasks(prev => [newTask, ...prev])
        setFileList([])

        notification.success({
          message: '文件上传成功',
          description: '文件已提交后台处理，请通过下方状态监控查看进度'
        })
      } else {
        throw new Error(response.error?.message || '上传失败')
      }
    } catch (error: any) {
      console.error('Upload error:', error)
      notification.error({
        message: '上传失败',
        description: error.message || '文件上传失败，请重试'
      })
      onUploadError?.(error)
    } finally {
      setUploading(false)
    }
  }, [fileList, priority, onUploadError])

  // 取消任务
  const handleCancelTask = useCallback(async (taskId: string) => {
    try {
      const response = await cancelTask(taskId)
      if (response.success) {
        setUploadTasks(prev => 
          prev.map(task => 
            task.taskId === taskId 
              ? { ...task, status: 'cancelled' as const }
              : task
          )
        )
        notification.success({
          message: '任务已取消',
          description: '任务已成功取消'
        })
      }
    } catch (error: any) {
      notification.error({
        message: '取消失败',
        description: error.message || '取消任务失败'
      })
    }
  }, [])

  // 更新任务状态
  React.useEffect(() => {
    if (taskStatus && currentTaskId) {
      setUploadTasks(prev => 
        prev.map(task => 
          task.taskId === currentTaskId
            ? { 
                ...task, 
                status: taskStatus.status.status as any
              }
            : task
        )
      )

      // 处理任务完成
      if (isCompleted && result) {
        notification.success({
          message: '处理完成',
          description: `文件处理成功！提取了 ${result.total_saved || 0} 个问答对`,
          duration: 5
        })
        onUploadComplete?.(result)
      }

      // 处理任务失败
      if (isFailed && error) {
        notification.error({
          message: '处理失败',
          description: error,
          duration: 5
        })
        onUploadError?.(error)
      }
    }
  }, [taskStatus, currentTaskId, isCompleted, isFailed, result, error, onUploadComplete, onUploadError])

  // 获取状态颜色
  const getStatusColor = (status: string) => {
    const colors: Record<string, string> = {
      pending: 'blue',
      running: 'orange',
      completed: 'green',
      failed: 'red',
      cancelled: 'gray'
    }
    return colors[status] || 'default'
  }

  // 获取状态图标
  const getStatusIcon = (status: string) => {
    const icons: Record<string, React.ReactNode> = {
      pending: <ClockCircleOutlined />,
      running: <ReloadOutlined spin />,
      completed: <CheckCircleOutlined />,
      failed: <CloseCircleOutlined />,
      cancelled: <StopOutlined />
    }
    return icons[status] || <InfoCircleOutlined />
  }

  // 获取优先级颜色
  const getPriorityColor = (priority: string) => {
    const colors: Record<string, string> = {
      low: 'blue',
      normal: 'default',
      high: 'orange',
      urgent: 'red'
    }
    return colors[priority] || 'default'
  }

  return (
    <div className="async-file-uploader">
      <Card title={
        <Space>
          <CloudUploadOutlined />
          <span>异步文件上传</span>
          <Tag color="blue">后台处理</Tag>
        </Space>
      }>
        <Space direction="vertical" size="large" style={{ width: '100%' }}>
          {/* 上传区域 */}
          <div>
            <Upload.Dragger
              ref={uploadRef}
              fileList={fileList}
              beforeUpload={beforeUpload}
              onChange={({ fileList }) => setFileList(fileList)}
              onRemove={() => setFileList([])}
              accept={allowedExtensions.join(',')}
              maxCount={1}
              showUploadList={{
                showRemoveIcon: true,
                showPreviewIcon: false
              }}
            >
              <p className="ant-upload-drag-icon">
                <UploadOutlined />
              </p>
              <p className="ant-upload-text">
                点击或拖拽文件到此区域上传
              </p>
              <p className="ant-upload-hint">
                支持 {allowedExtensions.join(', ')} 格式，最大 {maxFileSize}MB
              </p>
            </Upload.Dragger>
          </div>

          {/* 高级选项 */}
          {showAdvancedOptions && (
            <Collapse ghost>
              <Panel header="高级选项" key="advanced">
                <Space>
                  <div>
                    <Text>任务优先级：</Text>
                    <Select 
                      value={priority} 
                      onChange={setPriority}
                      style={{ width: 120 }}
                    >
                      <Option value="low">低</Option>
                      <Option value="normal">普通</Option>
                      <Option value="high">高</Option>
                      <Option value="urgent">紧急</Option>
                    </Select>
                  </div>
                  
                  <div>
                    <Text>自动刷新：</Text>
                    <Switch 
                      checked={autoRefresh}
                      onChange={setAutoRefresh}
                      size="small"
                    />
                  </div>
                </Space>
              </Panel>
            </Collapse>
          )}

          {/* 上传按钮 */}
          <Button
            type="primary"
            icon={<UploadOutlined />}
            loading={uploading}
            onClick={handleUpload}
            disabled={fileList.length === 0}
            size="large"
            block
          >
            {uploading ? '提交中...' : '提交到后台处理'}
          </Button>

          {/* 当前进度 */}
          {isLoading && currentTaskId && (
            <Card size="small" style={{ backgroundColor: '#f6ffed', border: '1px solid #b7eb8f' }}>
              <Space direction="vertical" style={{ width: '100%' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <Text strong>正在处理中...</Text>
                  <Button 
                    size="small" 
                    danger 
                    icon={<StopOutlined />}
                    onClick={() => handleCancelTask(currentTaskId)}
                  >
                    取消
                  </Button>
                </div>
                <Progress percent={50} status="active" showInfo={false} />
                <Text type="secondary">任务ID: {currentTaskId}</Text>
              </Space>
            </Card>
          )}

          {/* 处理结果提示 */}
          {isCompleted && result && (
            <Alert
              message="处理完成"
              description={
                <div>
                  <p>文件处理成功完成！</p>
                  <p>• 提取问答对：{result.total_extracted || 0} 个</p>
                  <p>• 保存记录：{result.total_saved || 0} 个</p>
                  <p>• 处理时间：{result.processing_time?.toFixed(2) || 0} 秒</p>
                </div>
              }
              type="success"
              showIcon
              closable
              onClose={clearStatus}
            />
          )}

          {isFailed && error && (
            <Alert
              message="处理失败"
              description={error}
              type="error"
              showIcon
              closable
              onClose={clearStatus}
            />
          )}
        </Space>
      </Card>

      {/* 任务历史 */}
      {uploadTasks.length > 0 && (
        <Card 
          title="处理任务"
          size="small"
          style={{ marginTop: 16 }}
        >
          <List
            size="small"
            dataSource={uploadTasks}
            renderItem={(task) => (
              <List.Item
                actions={[
                  <Tag color={getPriorityColor(task.priority)} key="priority">
                    {task.priority}
                  </Tag>,
                  task.status === 'running' ? (
                    <Button
                      size="small"
                      danger
                      icon={<StopOutlined />}
                      onClick={() => handleCancelTask(task.taskId)}
                      key="cancel"
                    >
                      取消
                    </Button>
                  ) : null
                ].filter(Boolean)}
              >
                <List.Item.Meta
                  avatar={getStatusIcon(task.status)}
                  title={
                    <Space>
                      <span>{task.filename}</span>
                      <Tag color={getStatusColor(task.status)}>
                        {task.status}
                      </Tag>
                    </Space>
                  }
                  description={
                    <Space>
                      <Text type="secondary">
                        上传时间：{task.uploadTime.toLocaleString()}
                      </Text>
                      <Text type="secondary" copyable>
                        任务ID：{task.taskId}
                      </Text>
                    </Space>
                  }
                />
              </List.Item>
            )}
          />
        </Card>
      )}
    </div>
  )
}

export default AsyncFileUploader