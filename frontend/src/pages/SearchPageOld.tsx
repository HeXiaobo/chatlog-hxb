import React, { useState, useEffect } from 'react'
import { Input, Card, List, Tag, Space, Pagination, Select, Spin, Empty } from 'antd'
import { SearchOutlined } from '@ant-design/icons'
import { useNavigate, useSearchParams } from 'react-router-dom'
import api from '../services/api'

const { Search } = Input
const { Option } = Select

interface Category {
  id: number
  name: string
  color: string
}

interface QAPair {
  id: number
  question: string
  answer: string
  category: Category
  advisor: string
  confidence: number
  created_at: string
}

const SearchPage: React.FC = () => {
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  
  const [loading, setLoading] = useState(false)
  const [categories, setCategories] = useState<Category[]>([])
  const [qas, setQAs] = useState<QAPair[]>([])
  const [total, setTotal] = useState(0)
  const [current, setCurrent] = useState(1)
  const [pageSize] = useState(20)
  
  const query = searchParams.get('q') || ''
  const categoryId = searchParams.get('category') || ''

  useEffect(() => {
    loadCategories()
  }, [])

  useEffect(() => {
    searchQAs()
  }, [searchParams, current])

  const loadCategories = async () => {
    try {
      const response = await api.get('/categories')
      setCategories(response.data.data || [])
    } catch (error) {
      console.error('Failed to load categories:', error)
    }
  }

  const searchQAs = async () => {
    setLoading(true)
    try {
      const params: any = {
        page: current,
        per_page: pageSize
      }
      
      if (query) params.q = query
      if (categoryId) params.category = categoryId
      
      const response = await api.get('/search/', { params })
      setQAs(response.data.data || [])
      setTotal(response.data.total || 0)
    } catch (error) {
      console.error('Failed to search QAs:', error)
      setQAs([])
      setTotal(0)
    } finally {
      setLoading(false)
    }
  }

  const handleSearch = (value: string) => {
    const newParams = new URLSearchParams(searchParams)
    if (value.trim()) {
      newParams.set('q', value)
    } else {
      newParams.delete('q')
    }
    setSearchParams(newParams)
    setCurrent(1)
  }

  const handleCategoryChange = (value: string) => {
    const newParams = new URLSearchParams(searchParams)
    if (value) {
      newParams.set('category', value)
    } else {
      newParams.delete('category')
    }
    setSearchParams(newParams)
    setCurrent(1)
  }

  const handlePageChange = (page: number) => {
    setCurrent(page)
  }

  const selectedCategory = categories.find(cat => cat.id.toString() === categoryId)

  return (
    <div>
      {/* 搜索区域 */}
      <Card style={{ marginBottom: 24 }}>
        <div style={{ maxWidth: 800, margin: '0 auto' }}>
          <Space.Compact style={{ width: '100%' }}>
            <Search
              placeholder="请输入关键词搜索..."
              defaultValue={query}
              enterButton={<SearchOutlined />}
              size="large"
              onSearch={handleSearch}
              style={{ flex: 1 }}
            />
            <Select
              placeholder="选择分类"
              size="large"
              style={{ width: 160 }}
              value={categoryId || undefined}
              onChange={handleCategoryChange}
              allowClear
            >
              {categories.map(category => (
                <Option key={category.id} value={category.id.toString()}>
                  {category.name}
                </Option>
              ))}
            </Select>
          </Space.Compact>
          
          {/* 搜索结果统计 */}
          <div style={{ marginTop: 16, color: '#666' }}>
            {query && (
              <span>搜索 "{query}" </span>
            )}
            {selectedCategory && (
              <span>在分类 "{selectedCategory.name}" 中 </span>
            )}
            共找到 <strong>{total}</strong> 条结果
          </div>
        </div>
      </Card>

      {/* 搜索结果 */}
      <Card>
        <Spin spinning={loading}>
          {qas.length > 0 ? (
            <>
              <List
                dataSource={qas}
                renderItem={item => (
                  <List.Item>
                    <Card
                      size="small"
                      style={{ width: '100%' }}
                      bodyStyle={{ padding: '16px' }}
                    >
                      <div style={{ marginBottom: 12 }}>
                        <h4 style={{ margin: 0, fontSize: '16px', fontWeight: 500 }}>
                          {item.question}
                        </h4>
                      </div>
                      
                      <div style={{ 
                        marginBottom: 12,
                        color: '#333',
                        lineHeight: '1.6'
                      }}>
                        {item.answer}
                      </div>
                      
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <Space size="small">
                          <Tag color={item.category?.color}>
                            {item.category?.name}
                          </Tag>
                          <span style={{ fontSize: '12px', color: '#999' }}>
                            by {item.advisor}
                          </span>
                          <span style={{ fontSize: '12px', color: '#999' }}>
                            置信度: {Math.round(item.confidence * 100)}%
                          </span>
                        </Space>
                        <span style={{ fontSize: '12px', color: '#999' }}>
                          {new Date(item.created_at).toLocaleDateString()}
                        </span>
                      </div>
                    </Card>
                  </List.Item>
                )}
              />
              
              {/* 分页 */}
              {total > pageSize && (
                <div style={{ textAlign: 'center', marginTop: 24 }}>
                  <Pagination
                    current={current}
                    total={total}
                    pageSize={pageSize}
                    onChange={handlePageChange}
                    showSizeChanger={false}
                    showQuickJumper
                    showTotal={(total, range) =>
                      `第 ${range[0]}-${range[1]} 条，共 ${total} 条`
                    }
                  />
                </div>
              )}
            </>
          ) : !loading ? (
            <Empty 
              description={
                query || categoryId 
                  ? "没有找到匹配的问答记录" 
                  : "请输入关键词进行搜索"
              }
            />
          ) : null}
        </Spin>
      </Card>
    </div>
  )
}

export default SearchPage