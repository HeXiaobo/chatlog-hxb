import React, { useState, useEffect } from 'react'
import { Card, Tabs, Input, Select, Space, Typography, Alert, Spin } from 'antd'
import { SearchOutlined, MessageOutlined, TeamOutlined, UserOutlined, ReloadOutlined } from '@ant-design/icons'
import SessionList from './SessionList'
import { chatlogService } from '../../services/chatlogService'
import type { ChatlogSession, BrowserFilter } from '../../types/chatlog'

const { TabPane } = Tabs
const { Text } = Typography

interface ChatlogBrowserProps {
  onSessionSelect: (session: ChatlogSession) => void
  selectedSession?: ChatlogSession
  height?: number
}

const ChatlogBrowser: React.FC<ChatlogBrowserProps> = ({
  onSessionSelect,
  selectedSession,
  height = 400
}) => {
  const [loading, setLoading] = useState(false)
  const [sessions, setSessions] = useState<ChatlogSession[]>([])
  const [filteredSessions, setFilteredSessions] = useState<ChatlogSession[]>([])
  const [activeTab, setActiveTab] = useState('all')
  const [filter, setFilter] = useState<BrowserFilter>({
    searchKeyword: '',
    sessionType: 'all',
    timeRange: 'all'
  })
  const [error, setError] = useState<string | null>(null)

  // 加载会话列表
  const loadSessions = async () => {
    setLoading(true)
    setError(null)
    
    try {
      const sessionList = await chatlogService.getSessionList()
      setSessions(sessionList)
      applyFilter(sessionList, filter)
    } catch (error: any) {
      console.error('Failed to load sessions:', error)
      setError(error.message || '加载会话列表失败')
      setSessions([])
      setFilteredSessions([])
    } finally {
      setLoading(false)
    }
  }

  // 应用筛选条件
  const applyFilter = (sessionList: ChatlogSession[], currentFilter: BrowserFilter) => {
    let filtered = sessionList

    // 根据activeTab筛选
    if (activeTab === 'groups') {
      filtered = filtered.filter(s => s.userName.includes('@chatroom'))
    } else if (activeTab === 'contacts') {
      filtered = filtered.filter(s => !s.userName.includes('@chatroom') && s.userName !== 'filehelper')
    } else if (activeTab === 'recent') {
      // 最近7天内有消息的会话
      const sevenDaysAgo = new Date()
      sevenDaysAgo.setDate(sevenDaysAgo.getDate() - 7)
      filtered = filtered.filter(s => new Date(s.nTime) >= sevenDaysAgo)
    }

    // 应用其他筛选条件
    if (currentFilter.searchKeyword && currentFilter.searchKeyword.trim()) {
      const keyword = currentFilter.searchKeyword.trim().toLowerCase()
      filtered = filtered.filter(session => 
        session.nickName.toLowerCase().includes(keyword) ||
        session.userName.toLowerCase().includes(keyword) ||
        session.content.toLowerCase().includes(keyword)
      )
    }

    setFilteredSessions(filtered)
  }

  // 处理搜索
  const handleSearch = (value: string) => {
    const newFilter = { ...filter, searchKeyword: value }
    setFilter(newFilter)
    applyFilter(sessions, newFilter)
  }

  // 处理tab切换
  const handleTabChange = (key: string) => {
    setActiveTab(key)
  }

  // 处理会话选择
  const handleSessionSelect = (session: ChatlogSession) => {
    onSessionSelect(session)
  }

  // 初始加载
  useEffect(() => {
    loadSessions()
  }, [])

  // 当activeTab变化时重新应用筛选
  useEffect(() => {
    applyFilter(sessions, filter)
  }, [activeTab, sessions])

  const getTabLabel = (key: string, icon: React.ReactNode, label: string) => {
    const count = key === 'all' ? sessions.length :
                  key === 'groups' ? sessions.filter(s => s.userName.includes('@chatroom')).length :
                  key === 'contacts' ? sessions.filter(s => !s.userName.includes('@chatroom') && s.userName !== 'filehelper').length :
                  sessions.filter(s => {
                    const sevenDaysAgo = new Date()
                    sevenDaysAgo.setDate(sevenDaysAgo.getDate() - 7)
                    return new Date(s.nTime) >= sevenDaysAgo
                  }).length

    return (
      <Space size={4}>
        {icon}
        <span>{label}</span>
        <Text type="secondary" style={{ fontSize: '12px' }}>({count})</Text>
      </Space>
    )
  }

  return (
    <Card 
      title="📱 选择聊天对象" 
      size="small"
      style={{ height }}
      bodyStyle={{ padding: 0, height: height - 57 }}
      extra={
        <Space>
          <Input
            placeholder="搜索群聊或联系人..."
            prefix={<SearchOutlined />}
            value={filter.searchKeyword}
            onChange={(e) => handleSearch(e.target.value)}
            style={{ width: 200 }}
            size="small"
            allowClear
          />
        </Space>
      }
    >
      {error && (
        <Alert
          message="加载失败"
          description={error}
          type="error"
          showIcon
          style={{ margin: 16, marginBottom: 0 }}
          action={
            <Text
              style={{ cursor: 'pointer', color: '#1890ff' }}
              onClick={loadSessions}
            >
              重试
            </Text>
          }
        />
      )}

      <Tabs 
        activeKey={activeTab} 
        onChange={handleTabChange}
        size="small"
        style={{ height: '100%' }}
        tabBarStyle={{ paddingLeft: 16, paddingRight: 16, marginBottom: 0 }}
      >
        <TabPane 
          tab={getTabLabel('recent', <MessageOutlined />, '最近会话')} 
          key="recent"
        >
          <div style={{ height: height - 100, overflow: 'hidden' }}>
            <SessionList
              sessions={filteredSessions}
              onSessionSelect={handleSessionSelect}
              selectedSession={selectedSession}
              loading={loading}
              emptyText="最近7天内没有活跃的会话"
            />
          </div>
        </TabPane>

        <TabPane 
          tab={getTabLabel('groups', <TeamOutlined />, '群聊')} 
          key="groups"
        >
          <div style={{ height: height - 100, overflow: 'hidden' }}>
            <SessionList
              sessions={filteredSessions}
              onSessionSelect={handleSessionSelect}
              selectedSession={selectedSession}
              loading={loading}
              emptyText="没有找到群聊"
            />
          </div>
        </TabPane>

        <TabPane 
          tab={getTabLabel('contacts', <UserOutlined />, '联系人')} 
          key="contacts"
        >
          <div style={{ height: height - 100, overflow: 'hidden' }}>
            <SessionList
              sessions={filteredSessions}
              onSessionSelect={handleSessionSelect}
              selectedSession={selectedSession}
              loading={loading}
              emptyText="没有找到联系人"
            />
          </div>
        </TabPane>

        <TabPane 
          tab={getTabLabel('all', <MessageOutlined />, '全部')} 
          key="all"
        >
          <div style={{ height: height - 100, overflow: 'hidden' }}>
            <SessionList
              sessions={filteredSessions}
              onSessionSelect={handleSessionSelect}
              selectedSession={selectedSession}
              loading={loading}
              emptyText="没有找到会话"
            />
          </div>
        </TabPane>
      </Tabs>
    </Card>
  )
}

export default ChatlogBrowser