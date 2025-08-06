import React, { useState, useCallback, useMemo, useRef, useEffect } from 'react'
import { 
  List, 
  Empty, 
  Spin, 
  Button, 
  Space, 
  Dropdown, 
  Select, 
  Checkbox,
  message,
  Modal
} from 'antd'
import {
  SortAscendingOutlined,
  SortDescendingOutlined,
  MoreOutlined,
  DeleteOutlined,
  TagOutlined,
  ExportOutlined,
  SelectOutlined
} from '@ant-design/icons'
import { FixedSizeList as VirtualList } from 'react-window'
import QACard from './QACard'
import type { QAPair, Category } from '../../types'

const { Option } = Select

interface QAListProps {
  data: QAPair[]
  categories?: Category[]
  loading?: boolean
  total?: number
  hasMore?: boolean
  highlight?: string
  compact?: boolean
  selectable?: boolean
  onLoadMore?: () => void
  onEdit?: (qa: QAPair) => void
  onDelete?: (id: number) => void
  onBulkDelete?: (ids: number[]) => void
  onCategoryChange?: (id: number, categoryId: number) => void
  onBulkCategoryChange?: (ids: number[], categoryId: number) => void
  onExport?: (ids: number[]) => void
  onStar?: (id: number, starred: boolean) => void
  className?: string
}

type SortField = 'created_at' | 'confidence' | 'question'
type SortOrder = 'asc' | 'desc'

interface SortConfig {
  field: SortField
  order: SortOrder
}

const QAList: React.FC<QAListProps> = ({
  data = [],
  categories = [],
  loading = false,
  total = 0,
  hasMore = false,
  highlight = '',
  compact = false,
  selectable = false,
  onLoadMore,
  onEdit,
  onDelete,
  onBulkDelete,
  onCategoryChange,
  onBulkCategoryChange,
  onExport,
  onStar,
  className = ''
}) => {
  const [selectedIds, setSelectedIds] = useState<number[]>([])
  const [sortConfig, setSortConfig] = useState<SortConfig>({
    field: 'created_at',
    order: 'desc'
  })
  const [starredItems, setStarredItems] = useState<Set<number>>(new Set())
  const listRef = useRef<VirtualList>(null)

  // 从 localStorage 加载收藏状态
  useEffect(() => {
    const starred = localStorage.getItem('starredQAs')
    if (starred) {
      try {
        const starredArray = JSON.parse(starred)
        setStarredItems(new Set(starredArray))
      } catch (error) {
        console.error('Failed to parse starred items:', error)
      }
    }
  }, [])

  const sortedData = useMemo(() => {
    if (!data.length) return []
    
    return [...data].sort((a, b) => {
      let aValue: any = a[sortConfig.field]
      let bValue: any = b[sortConfig.field]
      
      if (sortConfig.field === 'created_at') {
        aValue = new Date(aValue).getTime()
        bValue = new Date(bValue).getTime()
      }
      
      if (typeof aValue === 'string') {
        aValue = aValue.toLowerCase()
        bValue = bValue.toLowerCase()
      }
      
      if (aValue < bValue) return sortConfig.order === 'asc' ? -1 : 1
      if (aValue > bValue) return sortConfig.order === 'asc' ? 1 : -1
      return 0
    })
  }, [data, sortConfig])

  const handleSort = useCallback((field: SortField) => {
    setSortConfig(prev => ({
      field,
      order: prev.field === field && prev.order === 'asc' ? 'desc' : 'asc'
    }))
  }, [])

  const handleSelectAll = useCallback((checked: boolean) => {
    setSelectedIds(checked ? data.map(item => item.id) : [])
  }, [data])

  const handleSelectItem = useCallback((id: number, checked: boolean) => {
    setSelectedIds(prev => 
      checked ? [...prev, id] : prev.filter(item => item !== id)
    )
  }, [])

  const handleBulkDelete = useCallback(() => {
    if (selectedIds.length === 0) return
    
    Modal.confirm({
      title: '批量删除',
      content: `确定要删除选中的 ${selectedIds.length} 条问答记录吗？删除后无法恢复。`,
      okText: '删除',
      okType: 'danger',
      cancelText: '取消',
      onOk: () => {
        onBulkDelete?.(selectedIds)
        setSelectedIds([])
        message.success(`已删除 ${selectedIds.length} 条记录`)
      }
    })
  }, [selectedIds, onBulkDelete])

  const handleBulkCategoryChange = useCallback((categoryId: number) => {
    if (selectedIds.length === 0) return
    
    onBulkCategoryChange?.(selectedIds, categoryId)
    setSelectedIds([])
    message.success(`已修改 ${selectedIds.length} 条记录的分类`)
  }, [selectedIds, onBulkCategoryChange])

  const handleExport = useCallback(() => {
    if (selectedIds.length === 0) {
      message.warning('请先选择要导出的记录')
      return
    }
    
    onExport?.(selectedIds)
    message.success(`正在导出 ${selectedIds.length} 条记录`)
  }, [selectedIds, onExport])

  const handleStar = useCallback((id: number, starred: boolean) => {
    setStarredItems(prev => {
      const newSet = new Set(prev)
      if (starred) {
        newSet.add(id)
      } else {
        newSet.delete(id)
      }
      
      // 保存到 localStorage
      localStorage.setItem('starredQAs', JSON.stringify([...newSet]))
      return newSet
    })
    
    onStar?.(id, starred)
  }, [onStar])

  const bulkActions = useMemo(() => [
    {
      key: 'category',
      label: '修改分类',
      icon: <TagOutlined />,
      children: categories.map(category => ({
        key: `category-${category.id}`,
        label: (
          <Space>
            <span style={{
              display: 'inline-block',
              width: 8,
              height: 8,
              borderRadius: '50%',
              backgroundColor: category.color
            }} />
            {category.name}
          </Space>
        ),
        onClick: () => handleBulkCategoryChange(category.id)
      }))
    },
    {
      key: 'export',
      label: '导出选中',
      icon: <ExportOutlined />,
      onClick: handleExport
    },
    {
      key: 'delete',
      label: '删除选中',
      icon: <DeleteOutlined />,
      onClick: handleBulkDelete,
      danger: true
    }
  ], [categories, handleBulkCategoryChange, handleExport, handleBulkDelete])

  const sortOptions = [
    { field: 'created_at' as const, label: '创建时间' },
    { field: 'confidence' as const, label: '置信度' },
    { field: 'question' as const, label: '问题内容' }
  ]

  // 虚拟列表项渲染器
  const renderItem = useCallback(({ index, style }: { index: number; style: React.CSSProperties }) => {
    const qa = sortedData[index]
    if (!qa) return null

    return (
      <div style={style}>
        <div style={{ padding: compact ? '4px 0' : '8px 0' }}>
          <div style={{ display: 'flex', alignItems: 'flex-start', gap: selectable ? 12 : 0 }}>
            {selectable && (
              <Checkbox
                checked={selectedIds.includes(qa.id)}
                onChange={(e) => handleSelectItem(qa.id, e.target.checked)}
                style={{ marginTop: 8 }}
              />
            )}
            <div style={{ flex: 1 }}>
              <QACard
                qa={qa}
                categories={categories}
                compact={compact}
                highlight={highlight}
                starred={starredItems.has(qa.id)}
                onEdit={onEdit}
                onDelete={onDelete}
                onCategoryChange={onCategoryChange}
                onStar={handleStar}
              />
            </div>
          </div>
        </div>
      </div>
    )
  }, [
    sortedData, 
    compact, 
    selectable, 
    selectedIds, 
    categories, 
    highlight, 
    starredItems,
    onEdit, 
    onDelete, 
    onCategoryChange, 
    handleSelectItem, 
    handleStar
  ])

  if (loading && data.length === 0) {
    return (
      <div style={{ textAlign: 'center', padding: '40px 0' }}>
        <Spin size="large" />
      </div>
    )
  }

  if (data.length === 0) {
    return (
      <Empty
        description="暂无问答记录"
        image={Empty.PRESENTED_IMAGE_SIMPLE}
        style={{ padding: '40px 0' }}
      >
        <Button type="primary">上传聊天记录</Button>
      </Empty>
    )
  }

  const itemHeight = compact ? 120 : 200
  const listHeight = Math.min(800, data.length * itemHeight)

  return (
    <div className={`qa-list ${className}`}>
      {/* 工具栏 */}
      <div className="qa-list-toolbar">
        <Space>
          {selectable && (
            <>
              <Checkbox
                indeterminate={selectedIds.length > 0 && selectedIds.length < data.length}
                checked={selectedIds.length === data.length}
                onChange={(e) => handleSelectAll(e.target.checked)}
              >
                全选 {selectedIds.length > 0 && `(${selectedIds.length})`}
              </Checkbox>
              
              {selectedIds.length > 0 && (
                <Dropdown menu={{ items: bulkActions }} trigger={['click']}>
                  <Button icon={<MoreOutlined />}>
                    批量操作
                  </Button>
                </Dropdown>
              )}
            </>
          )}
          
          <Select
            value={`${sortConfig.field}-${sortConfig.order}`}
            style={{ width: 140 }}
            size="small"
            onChange={(value) => {
              const [field, order] = value.split('-') as [SortField, SortOrder]
              setSortConfig({ field, order })
            }}
          >
            {sortOptions.map(option => (
              <React.Fragment key={option.field}>
                <Option value={`${option.field}-desc`}>
                  <Space size="small">
                    <SortDescendingOutlined />
                    {option.label}
                  </Space>
                </Option>
                <Option value={`${option.field}-asc`}>
                  <Space size="small">
                    <SortAscendingOutlined />
                    {option.label}
                  </Space>
                </Option>
              </React.Fragment>
            ))}
          </Select>
          
          <div className="qa-list-info">
            共 {total || data.length} 条记录
          </div>
        </Space>
      </div>

      {/* 虚拟列表 */}
      <div className="qa-list-content">
        <VirtualList
          ref={listRef}
          height={listHeight}
          itemCount={sortedData.length}
          itemSize={itemHeight}
          overscanCount={5}
        >
          {renderItem}
        </VirtualList>
      </div>

      {/* 加载更多 */}
      {hasMore && (
        <div style={{ textAlign: 'center', padding: '16px 0' }}>
          <Button loading={loading} onClick={onLoadMore}>
            加载更多
          </Button>
        </div>
      )}

      {loading && data.length > 0 && (
        <div style={{ textAlign: 'center', padding: '16px 0' }}>
          <Spin />
        </div>
      )}

      <style jsx>{`
        .qa-list {
          background: #fff;
          border-radius: 8px;
          overflow: hidden;
        }
        
        .qa-list-toolbar {
          padding: 16px;
          border-bottom: 1px solid #f0f0f0;
          background: #fafafa;
          display: flex;
          justify-content: space-between;
          align-items: center;
        }
        
        .qa-list-info {
          color: #666;
          font-size: 12px;
        }
        
        .qa-list-content {
          padding: 16px;
        }
        
        @media (max-width: 768px) {
          .qa-list-toolbar {
            padding: 12px;
            flex-direction: column;
            gap: 12px;
            align-items: stretch;
          }
          
          .qa-list-content {
            padding: 12px;
          }
        }
      `}</style>
    </div>
  )
}

export default QAList