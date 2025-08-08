import React from 'react'
import { List, Avatar, Typography, Tag, Empty, Spin } from 'antd'
import { TeamOutlined, UserOutlined, RobotOutlined } from '@ant-design/icons'
import dayjs from 'dayjs'
import relativeTime from 'dayjs/plugin/relativeTime'
import 'dayjs/locale/zh-cn'
import type { ChatlogSession } from '../../types/chatlog'

// 配置dayjs
dayjs.extend(relativeTime)
dayjs.locale('zh-cn')

const { Text, Paragraph } = Typography

interface SessionListProps {
  sessions: ChatlogSession[]
  onSessionSelect: (session: ChatlogSession) => void
  selectedSession?: ChatlogSession
  loading?: boolean
  emptyText?: string
}

const SessionList: React.FC<SessionListProps> = ({
  sessions,
  onSessionSelect,
  selectedSession,
  loading = false,
  emptyText = '暂无数据'
}) => {
  // 获取会话类型图标
  const getSessionIcon = (session: ChatlogSession) => {
    if (session.userName === 'filehelper') {
      return <RobotOutlined style={{ color: '#52c41a' }} />
    } else if (session.userName.includes('@chatroom')) {
      return <TeamOutlined style={{ color: '#1890ff' }} />
    } else {
      return <UserOutlined style={{ color: '#faad14' }} />
    }
  }

  // 获取会话类型标签
  const getSessionType = (session: ChatlogSession) => {
    if (session.userName === 'filehelper') {
      return <Tag color="green" size="small">文件助手</Tag>
    } else if (session.userName.includes('@chatroom')) {
      return <Tag color="blue" size="small">群聊</Tag>
    } else if (session.userName.includes('@openim')) {
      return <Tag color="orange" size="small">企业微信</Tag>
    } else {
      return <Tag color="default" size="small">个人</Tag>
    }
  }

  // 格式化时间
  const formatTime = (timeStr: string) => {
    const time = dayjs(timeStr)
    const now = dayjs()
    
    if (time.isSame(now, 'day')) {
      return time.format('HH:mm')
    } else if (time.isSame(now.subtract(1, 'day'), 'day')) {
      return '昨天 ' + time.format('HH:mm')
    } else if (time.isAfter(now.subtract(7, 'day'))) {
      return time.format('MM-DD HH:mm')
    } else {
      return time.format('YYYY-MM-DD')
    }
  }

  // 截断显示文本
  const truncateText = (text: string, maxLength: number = 30) => {
    if (!text) return ''
    if (text.length <= maxLength) return text
    return text.slice(0, maxLength) + '...'
  }

  // 高亮搜索关键词（简单实现）
  const highlightKeyword = (text: string, keyword?: string) => {
    if (!keyword || !keyword.trim()) return text
    
    const index = text.toLowerCase().indexOf(keyword.toLowerCase())
    if (index === -1) return text
    
    return (
      <>
        {text.slice(0, index)}
        <span style={{ backgroundColor: '#fff566', padding: '0 2px' }}>
          {text.slice(index, index + keyword.length)}
        </span>
        {text.slice(index + keyword.length)}
      </>
    )
  }

  if (loading) {
    return (
      <div style={{ 
        display: 'flex', 
        justifyContent: 'center', 
        alignItems: 'center', 
        height: '200px' 
      }}>
        <Spin size="large" />
      </div>
    )
  }

  if (sessions.length === 0) {
    return (
      <Empty 
        description={emptyText}
        style={{ 
          marginTop: '60px',
          marginBottom: '60px'
        }}
      />
    )
  }

  return (
    <List
      dataSource={sessions}
      style={{ 
        height: '100%', 
        overflowY: 'auto',
        padding: '0 8px'
      }}
      renderItem={(session) => (
        <List.Item
          key={session.userName}
          onClick={() => onSessionSelect(session)}
          style={{
            cursor: 'pointer',
            backgroundColor: selectedSession?.userName === session.userName ? '#f0f8ff' : 'transparent',
            borderRadius: '6px',
            margin: '4px 0',
            padding: '8px 12px',
            border: selectedSession?.userName === session.userName ? '1px solid #d4edda' : '1px solid transparent',
            transition: 'all 0.2s'
          }}
          className="session-list-item"
        >
          <List.Item.Meta
            avatar={
              <Avatar 
                icon={getSessionIcon(session)} 
                style={{ backgroundColor: '#f5f5f5' }}
              />
            }
            title={
              <div style={{ 
                display: 'flex', 
                justifyContent: 'space-between', 
                alignItems: 'flex-start',
                marginBottom: '2px'
              }}>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <Text 
                    strong 
                    style={{ 
                      fontSize: '14px',
                      display: 'block',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap'
                    }}
                    title={session.nickName}
                  >
                    {highlightKeyword(session.nickName)}
                  </Text>
                </div>
                <div style={{ marginLeft: '8px', flexShrink: 0 }}>
                  <Text 
                    type="secondary" 
                    style={{ fontSize: '12px', whiteSpace: 'nowrap' }}
                  >
                    {formatTime(session.nTime)}
                  </Text>
                </div>
              </div>
            }
            description={
              <div>
                <div style={{ marginBottom: '4px' }}>
                  {getSessionType(session)}
                  <Text 
                    type="secondary" 
                    style={{ 
                      fontSize: '11px',
                      marginLeft: '8px',
                      fontFamily: 'monospace'
                    }}
                    copyable={{ text: session.userName }}
                    title="点击复制ID"
                  >
                    {truncateText(session.userName, 20)}
                  </Text>
                </div>
                {session.content && (
                  <Text 
                    type="secondary" 
                    style={{ 
                      fontSize: '12px',
                      lineHeight: '16px',
                      display: 'block'
                    }}
                  >
                    {highlightKeyword(truncateText(session.content, 40))}
                  </Text>
                )}
              </div>
            }
          />
        </List.Item>
      )}
    />
  )
}

// 添加CSS样式（通过styled-component或者CSS文件）
const styles = `
.session-list-item:hover {
  background-color: #fafafa !important;
  border-color: #d9d9d9 !important;
}
`

// 注入样式
if (typeof document !== 'undefined') {
  const styleElement = document.createElement('style')
  styleElement.textContent = styles
  document.head.appendChild(styleElement)
}

export default SessionList