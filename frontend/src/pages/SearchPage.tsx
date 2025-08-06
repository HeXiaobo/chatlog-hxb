import React, { useState, useEffect, useCallback } from 'react'
import { Card, Empty, Spin, Space, Button, message } from 'antd'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { ArrowLeftOutlined, ReloadOutlined } from '@ant-design/icons'
import SearchBar from '../components/search/SearchBar'
import QAList from '../components/qa/QAList'
import type { QAPair, Category, SearchFilters, APIResponse } from '../types'
import api from '../services/api'

const SearchPageNew: React.FC = () => {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const [loading, setLoading] = useState(false)
  const [categories, setCategories] = useState<Category[]>([])
  const [qaData, setQAData] = useState<QAPair[]>([])
  const [total, setTotal] = useState(0)
  const [currentPage, setCurrentPage] = useState(1)
  const [hasMore, setHasMore] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [searchFilters, setSearchFilters] = useState<SearchFilters>({})

  // 从URL参数获取初始搜索条件
  useEffect(() => {
    const query = searchParams.get('q') || ''
    const categoryId = searchParams.get('category')
    
    setSearchQuery(query)
    setSearchFilters({
      category_id: categoryId ? parseInt(categoryId) : undefined
    })
  }, [searchParams])

  // 加载分类数据
  useEffect(() => {
    loadCategories()
  }, [])

  // 执行搜索
  useEffect(() => {
    if (searchQuery || Object.keys(searchFilters).some(key => searchFilters[key as keyof SearchFilters])) {
      handleSearch(searchQuery, searchFilters, true)
    }
  }, [searchQuery, searchFilters])

  const loadCategories = async () => {
    try {
      const response = await api.get<APIResponse<Category[]>>('/categories')
      if (response.data.success && response.data.data) {
        setCategories(response.data.data)
      }
    } catch (error) {
      console.error('Failed to load categories:', error)
    }
  }

  const handleSearch = useCallback(async (
    query: string, 
    filters: SearchFilters = {}, 
    reset = false
  ) => {
    if (!query.trim() && !Object.keys(filters).some(key => filters[key as keyof SearchFilters])) {
      setQAData([])
      setTotal(0)
      return
    }

    if (reset) {
      setCurrentPage(1)
      setQAData([])
    }

    setLoading(true)
    try {
      const params = new URLSearchParams()
      if (query.trim()) {
        params.set('q', query)
      }
      if (filters.category_id) {
        params.set('category', filters.category_id.toString())
      }
      params.set('page', reset ? '1' : currentPage.toString())
      params.set('per_page', '20')

      const response = await api.get<APIResponse<QAPair[]>>(`/search?${params.toString()}`)
      
      if (response.data.success && response.data.data) {
        const newData = response.data.data
        setQAData(prev => reset ? newData : [...prev, ...newData])
        setTotal(response.data.total || 0)
        setHasMore((response.data.pagination?.page || 1) < (response.data.pagination?.pages || 1))
        
        if (reset) {
          setSearchQuery(query)
          setSearchFilters(filters)
        }
      } else {
        message.error(response.data.error?.message || '搜索失败')
      }
    } catch (error: any) {
      console.error('Search failed:', error)
      message.error(error.response?.data?.error?.message || '搜索失败')
    } finally {
      setLoading(false)
    }
  }, [currentPage])

  const handleLoadMore = useCallback(() => {
    setCurrentPage(prev => prev + 1)
    handleSearch(searchQuery, searchFilters, false)
  }, [searchQuery, searchFilters, handleSearch])

  const handleEditQA = useCallback((qa: QAPair) => {
    // TODO: 实现编辑功能
    message.info('编辑功能开发中')
  }, [])

  const handleDeleteQA = useCallback(async (id: number) => {
    try {
      await api.delete(`/qa/${id}`)
      setQAData(prev => prev.filter(item => item.id !== id))
      setTotal(prev => prev - 1)
      message.success('删除成功')
    } catch (error: any) {
      console.error('Delete failed:', error)
      message.error(error.response?.data?.error?.message || '删除失败')
    }
  }, [])

  const handleCategoryChange = useCallback(async (id: number, categoryId: number) => {
    try {
      await api.put(`/qa/${id}`, { category_id: categoryId })
      setQAData(prev => prev.map(item => 
        item.id === id 
          ? { ...item, category_id: categoryId, category: categories.find(cat => cat.id === categoryId) }
          : item
      ))
      message.success('分类修改成功')
    } catch (error: any) {
      console.error('Category change failed:', error)
      message.error(error.response?.data?.error?.message || '分类修改失败')
    }
  }, [categories])

  const handleBulkDelete = useCallback(async (ids: number[]) => {
    try {
      await Promise.all(ids.map(id => api.delete(`/qa/${id}`)))
      setQAData(prev => prev.filter(item => !ids.includes(item.id)))
      setTotal(prev => prev - ids.length)
      message.success(`已删除 ${ids.length} 条记录`)
    } catch (error: any) {
      console.error('Bulk delete failed:', error)
      message.error('批量删除失败')
    }
  }, [])

  const handleBulkCategoryChange = useCallback(async (ids: number[], categoryId: number) => {
    try {
      await Promise.all(ids.map(id => api.put(`/qa/${id}`, { category_id: categoryId })))
      const targetCategory = categories.find(cat => cat.id === categoryId)
      setQAData(prev => prev.map(item => 
        ids.includes(item.id) 
          ? { ...item, category_id: categoryId, category: targetCategory }
          : item
      ))
      message.success(`已修改 ${ids.length} 条记录的分类`)
    } catch (error: any) {
      console.error('Bulk category change failed:', error)
      message.error('批量分类修改失败')
    }
  }, [categories])

  const handleExport = useCallback((ids: number[]) => {
    // TODO: 实现导出功能
    message.info('导出功能开发中')
  }, [])

  const refreshSearch = () => {
    handleSearch(searchQuery, searchFilters, true)
  }

  return (
    <div className="search-page">
      {/* 页面头部 */}
      <Card style={{ marginBottom: 24 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
          <Button 
            icon={<ArrowLeftOutlined />} 
            onClick={() => navigate('/')}
            type="text"
          >
            返回首页
          </Button>
          <Button 
            icon={<ReloadOutlined />} 
            onClick={refreshSearch}
            loading={loading}
          >
            刷新
          </Button>
        </div>
        
        <SearchBar
          value={searchQuery}
          placeholder="请输入关键词搜索问答..."
          onSearch={handleSearch}
          categories={categories}
          showFilters={true}
          loading={loading}
        />
        
        {total > 0 && (
          <div style={{ marginTop: 16, textAlign: 'center', color: '#666' }}>
            找到 <strong>{total}</strong> 条相关记录
          </div>
        )}
      </Card>

      {/* 搜索结果 */}
      {qaData.length > 0 ? (
        <QAList
          data={qaData}
          categories={categories}
          loading={loading}
          total={total}
          hasMore={hasMore}
          highlight={searchQuery}
          selectable={true}
          onLoadMore={handleLoadMore}
          onEdit={handleEditQA}
          onDelete={handleDeleteQA}
          onBulkDelete={handleBulkDelete}
          onCategoryChange={handleCategoryChange}
          onBulkCategoryChange={handleBulkCategoryChange}
          onExport={handleExport}
        />
      ) : (
        <Card>
          {loading ? (
            <div style={{ textAlign: 'center', padding: '40px 0' }}>
              <Spin size="large" />
              <div style={{ marginTop: 16 }}>搜索中...</div>
            </div>
          ) : searchQuery || Object.keys(searchFilters).length > 0 ? (
            <Empty
              description={
                <Space direction="vertical">
                  <span>未找到相关问答记录</span>
                  <span style={{ color: '#999', fontSize: '12px' }}>
                    试试使用不同的关键词或筛选条件
                  </span>
                </Space>
              }
              image={Empty.PRESENTED_IMAGE_SIMPLE}
            >
              <Button onClick={() => {
                setSearchQuery('')
                setSearchFilters({})
                setQAData([])
                setTotal(0)
              }}>
                清空搜索
              </Button>
            </Empty>
          ) : (
            <Empty
              description="请输入关键词开始搜索"
              image={Empty.PRESENTED_IMAGE_SIMPLE}
            />
          )}
        </Card>
      )}

      <style jsx>{`
        .search-page {
          max-width: 1000px;
          margin: 0 auto;
        }
        
        @media (max-width: 768px) {
          .search-page {
            margin: 0;
          }
        }
      `}</style>
    </div>
  )
}

export default SearchPageNew