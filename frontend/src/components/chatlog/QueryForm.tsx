import React, { useState, useEffect } from 'react'
import { Form, DatePicker, Input, Button, Space, Card, Typography, Collapse, Divider } from 'antd'
import { SearchOutlined, ReloadOutlined, CalendarOutlined, DownOutlined } from '@ant-design/icons'
import dayjs, { Dayjs } from 'dayjs'
import ChatlogBrowser from './ChatlogBrowser'
import type { QueryParams, ChatlogSession } from '../../types/chatlog'

const { RangePicker } = DatePicker
const { Text } = Typography
const { Panel } = Collapse

interface QueryFormProps {
  onQuery: (params: QueryParams) => void
  loading?: boolean
  disabled?: boolean
}

interface FormValues {
  timeRange: [Dayjs, Dayjs] | null
  talker: string
  sender: string
  keyword: string
}

const QueryForm: React.FC<QueryFormProps> = ({
  onQuery,
  loading = false,
  disabled = false
}) => {
  const [form] = Form.useForm<FormValues>()
  const [selectedSession, setSelectedSession] = useState<ChatlogSession | undefined>()
  const [showBrowser, setShowBrowser] = useState(false)

  // 设置默认值
  useEffect(() => {
    const now = dayjs()
    const oneWeekAgo = now.subtract(7, 'day')
    
    form.setFieldsValue({
      timeRange: [oneWeekAgo, now],
      talker: '',
      sender: '',
      keyword: ''
    })
  }, [form])

  const handleSubmit = (values: FormValues) => {
    if (!values.timeRange || values.timeRange.length !== 2) {
      return
    }

    const [start, end] = values.timeRange
    const params: QueryParams = {
      timeRange: {
        start: start.format('YYYY-MM-DD'),
        end: end.format('YYYY-MM-DD')
      },
      format: 'json'
    }

    // 添加可选参数
    if (values.talker) {
      params.talker = values.talker
    }
    if (values.sender?.trim()) {
      params.sender = values.sender.trim()
    }
    if (values.keyword?.trim()) {
      params.keyword = values.keyword.trim()
    }

    console.log('Submitting query params:', params)
    onQuery(params)
  }

  const handleReset = () => {
    form.resetFields()
    const now = dayjs()
    const oneWeekAgo = now.subtract(7, 'day')
    
    form.setFieldsValue({
      timeRange: [oneWeekAgo, now],
      talker: '',
      sender: '',
      keyword: ''
    })
  }

  // 快捷时间选择
  const quickTimeRanges = [
    {
      label: '今天',
      value: () => [dayjs().startOf('day'), dayjs()]
    },
    {
      label: '昨天',
      value: () => [dayjs().subtract(1, 'day').startOf('day'), dayjs().subtract(1, 'day').endOf('day')]
    },
    {
      label: '最近3天',
      value: () => [dayjs().subtract(3, 'day'), dayjs()]
    },
    {
      label: '最近7天',
      value: () => [dayjs().subtract(7, 'day'), dayjs()]
    },
    {
      label: '最近30天',
      value: () => [dayjs().subtract(30, 'day'), dayjs()]
    }
  ]

  const handleQuickTime = (getValue: () => [Dayjs, Dayjs]) => {
    const timeRange = getValue()
    form.setFieldValue('timeRange', timeRange)
  }

  // 处理会话选择
  const handleSessionSelect = (session: ChatlogSession) => {
    setSelectedSession(session)
    form.setFieldValue('talker', session.userName)
    setShowBrowser(false)
  }

  // 清除会话选择
  const handleClearSession = () => {
    setSelectedSession(undefined)
    form.setFieldValue('talker', '')
  }

  return (
    <div>
      <Form
        form={form}
        layout="vertical"
        onFinish={handleSubmit}
        disabled={disabled}
        size="small"
      >
        {/* 时间范围 */}
        <Form.Item
          label="时间范围"
          name="timeRange"
          rules={[{ required: true, message: '请选择时间范围' }]}
        >
          <RangePicker
            style={{ width: '100%' }}
            format="YYYY-MM-DD"
            placeholder={['开始日期', '结束日期']}
            allowClear={false}
            showTime={false}
          />
        </Form.Item>

        {/* 快捷时间选择 */}
        <div style={{ marginBottom: 16 }}>
          <Text type="secondary" style={{ fontSize: '12px', display: 'block', marginBottom: 8 }}>
            快捷选择：
          </Text>
          <Space size="small" wrap>
            {quickTimeRanges.map((range, index) => (
              <Button
                key={index}
                size="small"
                type="text"
                onClick={() => handleQuickTime(range.value)}
                style={{ padding: '0 8px', height: '24px', fontSize: '12px' }}
              >
                {range.label}
              </Button>
            ))}
          </Space>
        </div>

        {/* 聊天对象选择 */}
        <Form.Item
          label="聊天对象"
          name="talker"
        >
          <div>
            {selectedSession ? (
              <Card 
                size="small" 
                style={{ 
                  backgroundColor: '#f0f8ff',
                  borderColor: '#d4edda',
                  marginBottom: 12
                }}
              >
                <div style={{ 
                  display: 'flex', 
                  justifyContent: 'space-between', 
                  alignItems: 'center' 
                }}>
                  <div>
                    <Text strong style={{ display: 'block' }}>
                      {selectedSession.nickName}
                    </Text>
                    <Text type="secondary" style={{ fontSize: '12px' }}>
                      {selectedSession.userName}
                    </Text>
                    <Text 
                      type="secondary" 
                      style={{ 
                        fontSize: '11px',
                        display: 'block',
                        marginTop: '2px'
                      }}
                    >
                      {selectedSession.userName.includes('@chatroom') ? '群聊' : '个人对话'}
                    </Text>
                  </div>
                  <Button 
                    type="text" 
                    size="small"
                    onClick={handleClearSession}
                  >
                    清除
                  </Button>
                </div>
              </Card>
            ) : (
              <div style={{ marginBottom: 12 }}>
                <Text type="secondary" style={{ fontSize: '13px' }}>
                  请选择要查询的聊天对象（可选）
                </Text>
              </div>
            )}

            <Collapse 
              size="small"
              activeKey={showBrowser ? ['browser'] : []}
              onChange={(keys) => setShowBrowser(keys.includes('browser'))}
            >
              <Panel 
                header={
                  <Space>
                    <SearchOutlined />
                    <span>浏览并选择聊天对象</span>
                  </Space>
                }
                key="browser"
              >
                <ChatlogBrowser
                  onSessionSelect={handleSessionSelect}
                  selectedSession={selectedSession}
                  height={350}
                />
              </Panel>
            </Collapse>
          </div>
        </Form.Item>

        {/* 发送者筛选 */}
        <Form.Item
          label="发送者筛选"
          name="sender"
        >
          <Input
            placeholder="发送者昵称（可选）"
            allowClear
          />
        </Form.Item>

        {/* 关键词搜索 */}
        <Form.Item
          label="关键词搜索"
          name="keyword"
        >
          <Input
            placeholder="搜索关键词（可选）"
            allowClear
          />
        </Form.Item>

        {/* 操作按钮 */}
        <Form.Item>
          <Space direction="vertical" style={{ width: '100%' }}>
            <Button
              type="primary"
              htmlType="submit"
              icon={<SearchOutlined />}
              loading={loading}
              block
            >
              查询聊天记录
            </Button>
            <Button
              type="default"
              onClick={handleReset}
              icon={<ReloadOutlined />}
              disabled={loading}
              block
            >
              重置条件
            </Button>
          </Space>
        </Form.Item>
      </Form>

      {/* 使用说明 */}
      <Card size="small" style={{ marginTop: 16, backgroundColor: '#fafafa' }}>
        <Text style={{ fontSize: '12px', color: '#666' }}>
          <div style={{ marginBottom: 8 }}>
            <strong>📋 使用说明：</strong>
          </div>
          <ul style={{ margin: 0, paddingLeft: 16 }}>
            <li>时间范围：必选，建议先选择较小范围测试</li>
            <li>聊天对象：可选，可浏览选择群聊或个人对话，不选择则查询所有对话</li>
            <li>发送者：可选，按发送者昵称筛选</li>
            <li>关键词：可选，在消息内容中搜索</li>
          </ul>
        </Text>
      </Card>
    </div>
  )
}

export default QueryForm