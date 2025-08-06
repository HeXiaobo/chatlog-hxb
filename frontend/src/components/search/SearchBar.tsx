import React, { useState, useCallback, useEffect } from 'react'
import { Input, Select, Button, Space, Dropdown, Badge, Tooltip, AutoComplete } from 'antd'
import { 
  SearchOutlined, 
  FilterOutlined, 
  ClearOutlined,
  HistoryOutlined,
  TagOutlined 
} from '@ant-design/icons'
import type { Category, SearchFilters, SearchSuggestion } from '../../types'

const { Search } = Input
const { Option } = Select

interface SearchBarProps {
  value?: string
  placeholder?: string
  onSearch: (query: string, filters?: SearchFilters) => void
  onSuggestionSelect?: (suggestion: SearchSuggestion) => void
  showFilters?: boolean
  categories: Category[]
  loading?: boolean
  className?: string
}

interface SearchState {
  query: string
  filters: SearchFilters
  suggestions: SearchSuggestion[]
  showAdvanced: boolean
  searchHistory: string[]
}

const SearchBar: React.FC<SearchBarProps> = ({
  value = '',
  placeholder = '请输入关键词搜索问答...',
  onSearch,
  onSuggestionSelect,
  showFilters = true,
  categories = [],
  loading = false,
  className = ''
}) => {
  const [state, setState] = useState<SearchState>({
    query: value,
    filters: {},
    suggestions: [],
    showAdvanced: false,
    searchHistory: []
  })

  // 从 localStorage 加载搜索历史
  useEffect(() => {
    const history = localStorage.getItem('searchHistory')
    if (history) {
      try {
        const parsedHistory = JSON.parse(history)
        setState(prev => ({ ...prev, searchHistory: parsedHistory.slice(0, 10) }))
      } catch (error) {
        console.error('Failed to parse search history:', error)
      }
    }
  }, [])

  // 保存搜索历史
  const saveSearchHistory = useCallback((query: string) => {
    if (!query.trim()) return
    
    setState(prev => {
      const newHistory = [query, ...prev.searchHistory.filter(item => item !== query)].slice(0, 10)
      localStorage.setItem('searchHistory', JSON.stringify(newHistory))
      return { ...prev, searchHistory: newHistory }
    })
  }, [])

  // 生成搜索建议
  const generateSuggestions = useCallback((query: string): SearchSuggestion[] => {
    if (!query.trim()) {
      return state.searchHistory.map(item => ({
        text: item,
        type: 'query' as const
      }))
    }

    const suggestions: SearchSuggestion[] = []
    
    // 搜索历史匹配
    state.searchHistory.forEach(item => {
      if (item.toLowerCase().includes(query.toLowerCase())) {
        suggestions.push({
          text: item,
          type: 'query'
        })
      }
    })

    // 分类匹配
    categories.forEach(category => {
      if (category.name.toLowerCase().includes(query.toLowerCase())) {
        suggestions.push({
          text: category.name,
          type: 'category',
          count: category.qa_count
        })
      }
    })

    return suggestions.slice(0, 8)
  }, [state.searchHistory, categories])

  const handleSearch = useCallback((searchQuery?: string) => {
    const finalQuery = searchQuery || state.query
    if (!finalQuery.trim() && !Object.keys(state.filters).length) return

    saveSearchHistory(finalQuery)
    onSearch(finalQuery, state.filters)
  }, [state.query, state.filters, onSearch, saveSearchHistory])

  const handleQueryChange = useCallback((newQuery: string) => {
    setState(prev => ({
      ...prev,
      query: newQuery,
      suggestions: generateSuggestions(newQuery)
    }))
  }, [generateSuggestions])

  const handleSuggestionSelect = useCallback((suggestion: string, option: any) => {
    const suggestionObj = option.suggestion
    setState(prev => ({ ...prev, query: suggestion, suggestions: [] }))
    
    if (suggestionObj?.type === 'category') {
      const category = categories.find(cat => cat.name === suggestion)
      if (category) {
        setState(prev => ({
          ...prev,
          filters: { ...prev.filters, category_id: category.id }
        }))
      }
    }
    
    onSuggestionSelect?.(suggestionObj)
    handleSearch(suggestion)
  }, [categories, onSuggestionSelect, handleSearch])

  const handleFilterChange = useCallback((key: keyof SearchFilters, value: any) => {
    setState(prev => ({
      ...prev,
      filters: { ...prev.filters, [key]: value }
    }))
  }, [])

  const clearFilters = useCallback(() => {
    setState(prev => ({
      ...prev,
      filters: {},
      showAdvanced: false
    }))
  }, [])

  const clearHistory = useCallback(() => {
    setState(prev => ({ ...prev, searchHistory: [] }))
    localStorage.removeItem('searchHistory')
  }, [])

  const activeFilterCount = Object.keys(state.filters).filter(key => 
    state.filters[key as keyof SearchFilters] !== undefined && 
    state.filters[key as keyof SearchFilters] !== ''
  ).length

  const autoCompleteOptions = state.suggestions.map((suggestion, index) => ({
    key: index,
    value: suggestion.text,
    label: (
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Space>
          {suggestion.type === 'query' && <HistoryOutlined />}
          {suggestion.type === 'category' && <TagOutlined />}
          <span>{suggestion.text}</span>
        </Space>
        {suggestion.count && (
          <Badge count={suggestion.count} style={{ backgroundColor: '#f0f0f0', color: '#999' }} />
        )}
      </div>
    ),
    suggestion
  }))

  const advancedFiltersDropdown = (
    <div style={{ padding: 16, minWidth: 300 }}>
      <Space direction="vertical" style={{ width: '100%' }}>
        <div>
          <label style={{ display: 'block', marginBottom: 4, fontWeight: 500 }}>分类筛选：</label>
          <Select
            placeholder="选择分类"
            style={{ width: '100%' }}
            allowClear
            value={state.filters.category_id}
            onChange={(value) => handleFilterChange('category_id', value)}
          >
            {categories.map(category => (
              <Option key={category.id} value={category.id}>
                <Space>
                  <span style={{ 
                    display: 'inline-block',
                    width: 8,
                    height: 8,
                    borderRadius: '50%',
                    backgroundColor: category.color
                  }} />
                  {category.name}
                  {category.qa_count && (
                    <Badge count={category.qa_count} style={{ backgroundColor: '#f0f0f0', color: '#999' }} />
                  )}
                </Space>
              </Option>
            ))}
          </Select>
        </div>
        
        <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 12 }}>
          <Button size="small" onClick={clearFilters} icon={<ClearOutlined />}>
            清除筛选
          </Button>
          <Button size="small" onClick={() => setState(prev => ({ ...prev, showAdvanced: false }))}>
            关闭
          </Button>
        </div>
      </Space>
    </div>
  )

  return (
    <div className={`search-bar ${className}`}>
      <Space.Compact style={{ width: '100%' }}>
        <AutoComplete
          value={state.query}
          options={autoCompleteOptions}
          onSelect={handleSuggestionSelect}
          onChange={handleQueryChange}
          style={{ flex: 1 }}
          onDropdownVisibleChange={(visible) => {
            if (visible && !state.query) {
              setState(prev => ({ ...prev, suggestions: generateSuggestions('') }))
            }
          }}
          dropdownRender={(menu) => (
            <div>
              {menu}
              {state.searchHistory.length > 0 && state.query === '' && (
                <div style={{ padding: '8px 16px', borderTop: '1px solid #f0f0f0' }}>
                  <Button 
                    type="link" 
                    size="small" 
                    onClick={clearHistory}
                    style={{ padding: 0 }}
                  >
                    清除搜索历史
                  </Button>
                </div>
              )}
            </div>
          )}
        >
          <Input
            placeholder={placeholder}
            suffix={
              <Button
                type="text"
                icon={<SearchOutlined />}
                loading={loading}
                onClick={() => handleSearch()}
              />
            }
            onPressEnter={() => handleSearch()}
          />
        </AutoComplete>
        
        {showFilters && (
          <Dropdown
            overlay={advancedFiltersDropdown}
            trigger={['click']}
            open={state.showAdvanced}
            onOpenChange={(visible) => setState(prev => ({ ...prev, showAdvanced: visible }))}
          >
            <Tooltip title="高级筛选">
              <Button 
                icon={<FilterOutlined />}
                style={{ 
                  borderColor: activeFilterCount > 0 ? '#1890ff' : undefined,
                  color: activeFilterCount > 0 ? '#1890ff' : undefined
                }}
              >
                {activeFilterCount > 0 && (
                  <Badge count={activeFilterCount} size="small" />
                )}
              </Button>
            </Tooltip>
          </Dropdown>
        )}
      </Space.Compact>

      <style jsx>{`
        .search-bar {
          width: 100%;
        }
        
        .search-bar .ant-select-dropdown {
          box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
        }
        
        @media (max-width: 768px) {
          .search-bar .ant-space-compact {
            flex-direction: column;
            gap: 8px;
          }
        }
      `}</style>
    </div>
  )
}

export default SearchBar