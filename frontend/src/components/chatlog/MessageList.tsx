import React, { useState, useMemo, useEffect } from 'react'
import { List, Checkbox, Button, Space, Typography, Tag, Card, Input, Select, Pagination, Empty, Alert } from 'antd'
import { SearchOutlined, UserOutlined, MessageOutlined, ClockCircleOutlined } from '@ant-design/icons'
import dayjs from 'dayjs'
import type { ChatlogMessage } from '../../types/chatlog'

const { Text } = Typography
const { Option } = Select
const { Search } = Input

interface MessageListProps {
  messages: ChatlogMessage[]
  selectedMessages: ChatlogMessage[]
  onSelectionChange: (selected: ChatlogMessage[]) => void
  loading?: boolean
}

const MessageList: React.FC<MessageListProps> = ({
  messages,
  selectedMessages,
  onSelectionChange,
  loading = false
}) => {
  const [currentPage, setCurrentPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)
  const [searchKeyword, setSearchKeyword] = useState('')
  const [senderFilter, setSenderFilter] = useState<string>('')
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())

  // 更新选中状态
  useEffect(() => {
    const ids = new Set(selectedMessages.map(msg => msg.id || msg.time + msg.senderName))
    setSelectedIds(ids)
  }, [selectedMessages])

  // 获取所有发送者
  const senders = useMemo(() => {
    const senderSet = new Set<string>()
    messages.forEach(msg => {
      if (msg.senderName) {
        senderSet.add(msg.senderName)
      }
    })
    return Array.from(senderSet).sort()
  }, [messages])

  // 过滤消息
  const filteredMessages = useMemo(() => {
    let filtered = [...messages]

    // 关键词搜索
    if (searchKeyword) {
      const keyword = searchKeyword.toLowerCase()
      filtered = filtered.filter(msg => {
        const content = extractMessageContent(msg).toLowerCase()
        const sender = msg.senderName?.toLowerCase() || ''
        return content.includes(keyword) || sender.includes(keyword)
      })
    }

    // 发送者筛选
    if (senderFilter) {
      filtered = filtered.filter(msg => msg.senderName === senderFilter)
    }

    return filtered
  }, [messages, searchKeyword, senderFilter])

  // 分页数据
  const paginatedMessages = useMemo(() => {
    const startIndex = (currentPage - 1) * pageSize
    const endIndex = startIndex + pageSize
    return filteredMessages.slice(startIndex, endIndex)
  }, [filteredMessages, currentPage, pageSize])

  // 提取消息内容
  const extractMessageContent = (msg: ChatlogMessage): string => {
    if (msg.contents?.desc) {
      return msg.contents.desc
    }
    if (msg.contents?.recordInfo?.DataList?.DataItems) {
      for (const item of msg.contents.recordInfo.DataList.DataItems) {
        if (item.DataDesc) {
          return item.DataDesc
        }
      }
    }
    return msg.content || ''
  }

  // 处理单个消息选择
  const handleMessageSelect = (msg: ChatlogMessage, checked: boolean) => {
    const msgId = msg.id || msg.time + msg.senderName
    const newSelectedIds = new Set(selectedIds)
    
    if (checked) {
      newSelectedIds.add(msgId)
    } else {
      newSelectedIds.delete(msgId)
    }
    
    setSelectedIds(newSelectedIds)
    
    // 更新选中的消息列表
    const newSelected = messages.filter(m => {
      const id = m.id || m.time + m.senderName
      return newSelectedIds.has(id)
    })
    
    onSelectionChange(newSelected)
  }

  // 处理全选/取消全选
  const handleSelectAll = (checked: boolean) => {
    if (checked) {
      const allIds = new Set(messages.map(msg => msg.id || msg.time + msg.senderName))
      setSelectedIds(allIds)
      onSelectionChange([...messages])
    } else {
      setSelectedIds(new Set())
      onSelectionChange([])
    }
  }

  // 处理当前页全选
  const handleSelectCurrentPage = (checked: boolean) => {
    const currentPageIds = paginatedMessages.map(msg => msg.id || msg.time + msg.senderName)
    const newSelectedIds = new Set(selectedIds)
    
    if (checked) {
      currentPageIds.forEach(id => newSelectedIds.add(id))
    } else {
      currentPageIds.forEach(id => newSelectedIds.delete(id))
    }
    
    setSelectedIds(newSelectedIds)
    
    const newSelected = messages.filter(m => {
      const id = m.id || m.time + m.senderName
      return newSelectedIds.has(id)
    })
    
    onSelectionChange(newSelected)
  }

  // 检查是否全选
  const isAllSelected = messages.length > 0 && selectedIds.size === messages.length
  const isCurrentPageSelected = paginatedMessages.length > 0 && 
    paginatedMessages.every(msg => selectedIds.has(msg.id || msg.time + msg.senderName))

  // 格式化时间
  const formatTime = (timeStr: string): string => {
    try {
      return dayjs(timeStr).format('MM-DD HH:mm')
    } catch {
      return timeStr
    }
  }

  // 判断消息质量（用于显示推荐标签）
  const getMessageQuality = (content: string): 'high' | 'medium' | 'low' => {
    if (!content) return 'low'
    
    // 简单的质量评估逻辑
    if (content.length < 10) return 'low'
    if (content.includes('?') || content.includes('？') || 
        content.includes('怎么') || content.includes('如何') || 
        content.includes('请问')) {
      return 'high' // 可能是问题
    }
    if (content.length > 30) return 'medium'
    return 'low'
  }

  if (messages.length === 0) {
    return (
      <Empty
        image={Empty.PRESENTED_IMAGE_SIMPLE}
        description="暂无聊天记录"
        style={{ padding: '40px 0' }}
      />
    )
  }

  return (
    <div>
      {/* 筛选和操作栏 */}
      <Card size="small" style={{ marginBottom: 16 }}>
        <Space direction="vertical" style={{ width: '100%' }}>
          {/* 搜索和筛选 */}
          <Space wrap style={{ width: '100%' }}>
            <Search
              placeholder="搜索消息内容或发送者"
              value={searchKeyword}
              onChange={(e) => setSearchKeyword(e.target.value)}
              style={{ width: 200 }}
              allowClear
            />
            <Select
              placeholder="按发送者筛选"
              value={senderFilter}
              onChange={setSenderFilter}
              style={{ width: 150 }}
              allowClear
            >
              {senders.map(sender => (
                <Option key={sender} value={sender}>
                  {sender}
                </Option>
              ))}
            </Select>
          </Space>

          {/* 批量操作 */}
          <Space>
            <Checkbox
              checked={isAllSelected}
              indeterminate={selectedIds.size > 0 && selectedIds.size < messages.length}
              onChange={(e) => handleSelectAll(e.target.checked)}
            >
              全选 ({messages.length}条)
            </Checkbox>
            <Checkbox
              checked={isCurrentPageSelected}
              onChange={(e) => handleSelectCurrentPage(e.target.checked)}
            >
              当前页全选
            </Checkbox>
            <Text type="secondary">
              已选择 {selectedIds.size} 条消息
            </Text>
          </Space>
        </Space>
      </Card>

      {/* 统计信息 */}
      {filteredMessages.length !== messages.length && (
        <Alert
          message={`筛选结果：显示 ${filteredMessages.length} 条，共 ${messages.length} 条记录`}
          type="info"
          style={{ marginBottom: 16 }}
          showIcon
        />
      )}

      {/* 消息列表 */}
      <List
        loading={loading}
        dataSource={paginatedMessages}
        renderItem={(item) => {
          const msgId = item.id || item.time + item.senderName
          const content = extractMessageContent(item)
          const quality = getMessageQuality(content)
          const isSelected = selectedIds.has(msgId)
          
          return (
            <List.Item
              style={{
                background: isSelected ? '#e6f7ff' : 'transparent',
                border: isSelected ? '1px solid #1890ff' : '1px solid #f0f0f0',
                borderRadius: 6,
                marginBottom: 8,
                padding: '12px 16px'
              }}
            >
              <div style={{ width: '100%' }}>
                <div style={{ display: 'flex', alignItems: 'flex-start', gap: 12 }}>
                  {/* 选择框 */}
                  <Checkbox
                    checked={isSelected}
                    onChange={(e) => handleMessageSelect(item, e.target.checked)}
                    style={{ marginTop: 2 }}
                  />
                  
                  {/* 消息内容 */}
                  <div style={{ flex: 1, minWidth: 0 }}>
                    {/* 消息头部 */}
                    <div style={{ display: 'flex', alignItems: 'center', marginBottom: 8, gap: 8 }}>
                      <Tag icon={<UserOutlined />} color="blue">
                        {item.senderName}
                      </Tag>
                      <Text type="secondary" style={{ fontSize: '12px' }}>
                        <ClockCircleOutlined style={{ marginRight: 4 }} />
                        {formatTime(item.time)}
                      </Text>
                      {quality === 'high' && (
                        <Tag color="green" style={{ fontSize: '10px' }}>
                          推荐
                        </Tag>
                      )}
                    </div>
                    
                    {/* 消息内容 */}
                    <div style={{ 
                      fontSize: '14px',
                      lineHeight: '1.5',
                      wordBreak: 'break-word',
                      color: '#262626',
                      background: '#fafafa',
                      padding: '8px 12px',
                      borderRadius: 4,
                      border: '1px solid #f0f0f0'
                    }}>
                      {content || '(无内容)'}
                    </div>
                    
                    {/* 消息元数据 */}
                    <div style={{ marginTop: 8, display: 'flex', gap: 8, alignItems: 'center' }}>
                      <Text type="secondary" style={{ fontSize: '12px' }}>
                        类型: {item.type || 'text'}
                      </Text>
                      <Text type="secondary" style={{ fontSize: '12px' }}>
                        长度: {content.length}字符
                      </Text>
                      {item.contents && (
                        <Tag color="orange" style={{ fontSize: '10px' }}>
                          复合内容
                        </Tag>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            </List.Item>
          )
        }}
      />

      {/* 分页 */}
      {filteredMessages.length > pageSize && (
        <div style={{ textAlign: 'center', marginTop: 16, padding: '16px 0', borderTop: '1px solid #f0f0f0' }}>
          <Pagination
            current={currentPage}
            total={filteredMessages.length}
            pageSize={pageSize}
            onChange={(page, size) => {
              setCurrentPage(page)
              if (size) setPageSize(size)
            }}
            showSizeChanger
            showQuickJumper
            showTotal={(total, range) => `${range[0]}-${range[1]} 共 ${total} 条`}
            pageSizeOptions={['10', '20', '50', '100']}
          />
        </div>
      )}
    </div>
  )
}

export default MessageList