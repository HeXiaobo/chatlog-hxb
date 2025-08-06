import React, { useState, useEffect } from 'react'
import { Card, Row, Col, Statistic, Button, List, Tag, Space, Modal, Alert } from 'antd'
import { SearchOutlined, QuestionCircleOutlined, TagOutlined, UploadOutlined, ExclamationCircleOutlined } from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import SearchBar from '../components/search/SearchBar'
import UploadZone from '../components/upload/UploadZone'
import type { Category, QAPair, APIResponse, SearchFilters, UploadResponse } from '../types'
import api from '../services/api'

const HomePage: React.FC = () => {
  const navigate = useNavigate()
  const [loading, setLoading] = useState(false)
  const [categories, setCategories] = useState<Category[]>([])
  const [recentQAs, setRecentQAs] = useState<QAPair[]>([])
  const [stats, setStats] = useState({
    totalQAs: 0,
    totalCategories: 0,
    totalUploads: 0
  })
  const [uploadModalVisible, setUploadModalVisible] = useState(false)
  const [apiError, setApiError] = useState<string | null>(null)

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    setLoading(true)
    setApiError(null)
    try {
      // 加载分类
      const categoriesResponse = await api.get<APIResponse<Category[]>>('/categories')
      setCategories(categoriesResponse.data.data || [])

      // 加载最近的问答
      const qasResponse = await api.get<APIResponse<QAPair[]>>('/qa?limit=5')
      setRecentQAs(qasResponse.data.data || [])

      // 设置统计数据
      setStats({
        totalQAs: qasResponse.data.total || 0,
        totalCategories: categoriesResponse.data.data?.length || 0,
        totalUploads: 0 // 暂时设为0，需要后端支持
      })
    } catch (error) {
      console.error('Failed to load data:', error)
      setApiError('后端服务暂时不可用，当前为演示模式。完整功能需要部署后端服务。')
      // API 调用失败时，设置默认数据以避免页面空白
      setCategories([
        { id: 1, name: '产品咨询', description: '产品相关问题', color: 'blue', qa_count: 0 },
        { id: 2, name: '技术支持', description: '技术问题解答', color: 'green', qa_count: 0 },
        { id: 3, name: '价格费用', description: '价格和费用咨询', color: 'orange', qa_count: 0 },
        { id: 4, name: '使用教程', description: '使用方法指导', color: 'purple', qa_count: 0 },
        { id: 5, name: '售后问题', description: '售后服务相关', color: 'red', qa_count: 0 }
      ])
      setRecentQAs([])
      setStats({ totalQAs: 0, totalCategories: 5, totalUploads: 0 })
    } finally {
      setLoading(false)
    }
  }

  const handleSearch = (query: string, filters?: SearchFilters) => {
    const params = new URLSearchParams()
    if (query.trim()) {
      params.set('q', query)
    }
    if (filters?.category_id) {
      params.set('category', filters.category_id.toString())
    }
    navigate(`/search?${params.toString()}`)
  }

  const handleUploadSuccess = (response: UploadResponse) => {
    setUploadModalVisible(false)
    loadData() // 重新加载数据
  }

  return (
    <div>
      {/* API 错误提示 */}
      {apiError && (
        <Alert
          message="服务状态提示"
          description={apiError}
          type="warning"
          icon={<ExclamationCircleOutlined />}
          showIcon
          closable
          style={{ marginBottom: 24 }}
          onClose={() => setApiError(null)}
        />
      )}

      {/* 搜索区域 */}
      <Card style={{ marginBottom: 24, textAlign: 'center' }}>
        <div style={{ maxWidth: 600, margin: '0 auto' }}>
          <h2 style={{ marginBottom: 24 }}>搜索知识库</h2>
          <SearchBar
            placeholder="请输入关键词搜索问答..."
            onSearch={handleSearch}
            categories={categories}
            showFilters={true}
          />
          <div style={{ marginTop: 16 }}>
            <Space>
              <p style={{ color: '#666', margin: 0 }}>
                已收录 <strong>{stats.totalQAs}</strong> 条问答记录
              </p>
              <Button 
                type="primary" 
                icon={<UploadOutlined />}
                onClick={() => setUploadModalVisible(true)}
              >
                上传文件
              </Button>
            </Space>
          </div>
        </div>
      </Card>

      {/* 统计数据 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={8}>
          <Card>
            <Statistic
              title="问答总数"
              value={stats.totalQAs}
              prefix={<QuestionCircleOutlined />}
              loading={loading}
            />
          </Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card>
            <Statistic
              title="分类数量"
              value={stats.totalCategories}
              prefix={<TagOutlined />}
              loading={loading}
            />
          </Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card>
            <Statistic
              title="上传次数"
              value={stats.totalUploads}
              prefix={<SearchOutlined />}
              loading={loading}
            />
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]}>
        {/* 分类列表 */}
        <Col xs={24} lg={12}>
          <Card title="知识分类" loading={loading}>
            <div>
              {categories.map(category => (
                <Card.Grid
                  key={category.id}
                  style={{ width: '50%', textAlign: 'center', cursor: 'pointer' }}
                  onClick={() => navigate(`/search?category=${category.id}`)}
                >
                  <Tag color={category.color} style={{ marginBottom: 8 }}>
                    {category.name}
                  </Tag>
                  <div style={{ fontSize: '12px', color: '#666' }}>
                    {category.description}
                  </div>
                  <div style={{ fontSize: '12px', marginTop: 4 }}>
                    {category.qa_count || 0} 条记录
                  </div>
                </Card.Grid>
              ))}
            </div>
          </Card>
        </Col>

        {/* 最新问答 */}
        <Col xs={24} lg={12}>
          <Card title="最新问答" loading={loading}>
            <List
              size="small"
              dataSource={recentQAs}
              renderItem={item => (
                <List.Item>
                  <div style={{ width: '100%' }}>
                    <div style={{ fontWeight: 500, marginBottom: 4 }}>
                      {item.question}
                    </div>
                    <div style={{ 
                      fontSize: '12px', 
                      color: '#666',
                      marginBottom: 8,
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap'
                    }}>
                      {item.answer}
                    </div>
                    <Space size="small">
                      <Tag color={item.category?.color}>{item.category?.name}</Tag>
                      <span style={{ fontSize: '12px', color: '#999' }}>
                        by {item.advisor}
                      </span>
                    </Space>
                  </div>
                </List.Item>
              )}
            />
            <div style={{ textAlign: 'center', marginTop: 16 }}>
              <Button onClick={() => navigate('/search')}>
                查看更多
              </Button>
            </div>
          </Card>
        </Col>
      </Row>

      {/* 上传弹窗 */}
      <Modal
        title="上传微信聊天记录"
        open={uploadModalVisible}
        onCancel={() => setUploadModalVisible(false)}
        footer={null}
        width={680}
        destroyOnClose
      >
        <UploadZone
          onUploadSuccess={handleUploadSuccess}
          onUploadError={(error) => console.error('Upload error:', error)}
        />
      </Modal>
    </div>
  )
}

export default HomePage