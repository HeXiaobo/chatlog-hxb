import React, { useState, useCallback } from 'react'
import { 
  Card, 
  Typography, 
  Tag, 
  Space, 
  Button, 
  Dropdown, 
  Progress,
  Tooltip,
  message,
  Modal,
  Select
} from 'antd'
import {
  MoreOutlined,
  CopyOutlined,
  EditOutlined,
  DeleteOutlined,
  ShareAltOutlined,
  StarOutlined,
  StarFilled,
  TagOutlined,
  UserOutlined,
  ClockCircleOutlined
} from '@ant-design/icons'
import type { QAPair, Category } from '../../types'

const { Text, Paragraph } = Typography
const { Option } = Select

interface QACardProps {
  qa: QAPair
  categories?: Category[]
  showActions?: boolean
  compact?: boolean
  highlight?: string
  starred?: boolean
  onEdit?: (qa: QAPair) => void
  onDelete?: (id: number) => void
  onCategoryChange?: (id: number, categoryId: number) => void
  onStar?: (id: number, starred: boolean) => void
  onShare?: (qa: QAPair) => void
  className?: string
}

const QACard: React.FC<QACardProps> = ({
  qa,
  categories = [],
  showActions = true,
  compact = false,
  highlight = '',
  starred = false,
  onEdit,
  onDelete,
  onCategoryChange,
  onStar,
  onShare,
  className = ''
}) => {
  const [expanded, setExpanded] = useState(false)
  const [categoryModalVisible, setCategoryModalVisible] = useState(false)
  const [selectedCategoryId, setSelectedCategoryId] = useState<number>(qa.category_id)

  const getConfidenceColor = useCallback((confidence: number): string => {
    if (confidence >= 0.8) return '#52c41a'
    if (confidence >= 0.6) return '#faad14'
    return '#f5222d'
  }, [])

  const getConfidenceText = useCallback((confidence: number): string => {
    if (confidence >= 0.8) return '高'
    if (confidence >= 0.6) return '中'
    return '低'
  }, [])

  const highlightText = useCallback((text: string, highlight: string): React.ReactNode => {
    if (!highlight) return text
    
    const parts = text.split(new RegExp(`(${highlight})`, 'gi'))
    return parts.map((part, index) => 
      part.toLowerCase() === highlight.toLowerCase() ? 
        <mark key={index} style={{ backgroundColor: '#fff3cd', padding: '0 2px' }}>{part}</mark> : 
        part
    )
  }, [])

  const handleCopy = useCallback(() => {
    const text = `问：${qa.question}\n\n答：${qa.answer}`
    navigator.clipboard.writeText(text).then(() => {
      message.success('已复制到剪贴板')
    }).catch(() => {
      message.error('复制失败')
    })
  }, [qa])

  const handleDelete = useCallback(() => {
    Modal.confirm({
      title: '确认删除',
      content: '确定要删除这条问答记录吗？删除后无法恢复。',
      okText: '删除',
      okType: 'danger',
      cancelText: '取消',
      onOk: () => onDelete?.(qa.id)
    })
  }, [qa.id, onDelete])

  const handleCategoryChange = useCallback(() => {
    if (selectedCategoryId !== qa.category_id) {
      onCategoryChange?.(qa.id, selectedCategoryId)
      setCategoryModalVisible(false)
      message.success('分类修改成功')
    } else {
      setCategoryModalVisible(false)
    }
  }, [qa.id, qa.category_id, selectedCategoryId, onCategoryChange])

  const formatDate = useCallback((dateString: string): string => {
    const date = new Date(dateString)
    const now = new Date()
    const diff = now.getTime() - date.getTime()
    const days = Math.floor(diff / (1000 * 60 * 60 * 24))
    
    if (days === 0) return '今天'
    if (days === 1) return '昨天'
    if (days < 7) return `${days}天前`
    if (days < 30) return `${Math.floor(days / 7)}周前`
    return date.toLocaleDateString('zh-CN')
  }, [])

  const actionItems = [
    {
      key: 'edit',
      label: '编辑',
      icon: <EditOutlined />,
      onClick: () => onEdit?.(qa)
    },
    {
      key: 'category',
      label: '修改分类',
      icon: <TagOutlined />,
      onClick: () => setCategoryModalVisible(true)
    },
    {
      key: 'copy',
      label: '复制内容',
      icon: <CopyOutlined />,
      onClick: handleCopy
    },
    {
      key: 'share',
      label: '分享',
      icon: <ShareAltOutlined />,
      onClick: () => onShare?.(qa)
    },
    {
      key: 'delete',
      label: '删除',
      icon: <DeleteOutlined />,
      onClick: handleDelete,
      danger: true
    }
  ]

  const maxLength = compact ? 100 : 200
  const shouldTruncateAnswer = qa.answer.length > maxLength
  const displayAnswer = expanded || !shouldTruncateAnswer ? 
    qa.answer : 
    qa.answer.substring(0, maxLength) + '...'

  return (
    <>
      <Card
        className={`qa-card ${compact ? 'compact' : ''} ${className}`}
        size={compact ? 'small' : 'default'}
        actions={showActions && !compact ? [
          <Tooltip title={starred ? '取消收藏' : '收藏'}>
            <Button
              type="text"
              icon={starred ? <StarFilled style={{ color: '#faad14' }} /> : <StarOutlined />}
              onClick={() => onStar?.(qa.id, !starred)}
            />
          </Tooltip>,
          <Tooltip title="复制内容">
            <Button type="text" icon={<CopyOutlined />} onClick={handleCopy} />
          </Tooltip>,
          <Dropdown menu={{ items: actionItems }} trigger={['click']}>
            <Button type="text" icon={<MoreOutlined />} />
          </Dropdown>
        ] : undefined}
      >
        <div className="qa-content">
          {/* 问题部分 */}
          <div className="question-section">
            <Text strong className="question-text">
              {highlightText(qa.question, highlight)}
            </Text>
          </div>

          {/* 答案部分 */}
          <div className="answer-section" style={{ marginTop: 12 }}>
            <Paragraph 
              className="answer-text"
              style={{ 
                marginBottom: shouldTruncateAnswer ? 8 : 16,
                whiteSpace: 'pre-wrap' 
              }}
            >
              {highlightText(displayAnswer, highlight)}
            </Paragraph>
            
            {shouldTruncateAnswer && (
              <Button 
                type="link" 
                size="small"
                style={{ padding: 0, height: 'auto' }}
                onClick={() => setExpanded(!expanded)}
              >
                {expanded ? '收起' : '展开'}
              </Button>
            )}
          </div>

          {/* 元信息部分 */}
          <div className="meta-section">
            <Space wrap size="small">
              {/* 分类标签 */}
              {qa.category && (
                <Tag color={qa.category.color} style={{ margin: 0 }}>
                  {qa.category.name}
                </Tag>
              )}

              {/* 置信度 */}
              <Tooltip title={`置信度: ${(qa.confidence * 100).toFixed(1)}%`}>
                <div className="confidence-indicator">
                  <Progress
                    type="circle"
                    size={16}
                    percent={qa.confidence * 100}
                    strokeColor={getConfidenceColor(qa.confidence)}
                    showInfo={false}
                    strokeWidth={8}
                  />
                  <Text 
                    style={{ 
                      fontSize: 12, 
                      color: getConfidenceColor(qa.confidence),
                      marginLeft: 4 
                    }}
                  >
                    {getConfidenceText(qa.confidence)}
                  </Text>
                </div>
              </Tooltip>

              {/* 回答者 */}
              {qa.advisor && (
                <Text type="secondary" style={{ fontSize: 12 }}>
                  <UserOutlined style={{ marginRight: 2 }} />
                  {qa.advisor}
                </Text>
              )}

              {/* 时间 */}
              <Text type="secondary" style={{ fontSize: 12 }}>
                <ClockCircleOutlined style={{ marginRight: 2 }} />
                {formatDate(qa.created_at)}
              </Text>
            </Space>

            {/* 紧凑模式下的快捷操作 */}
            {showActions && compact && (
              <div className="compact-actions">
                <Space size="small">
                  <Button
                    type="text"
                    size="small"
                    icon={starred ? <StarFilled style={{ color: '#faad14' }} /> : <StarOutlined />}
                    onClick={() => onStar?.(qa.id, !starred)}
                  />
                  <Button
                    type="text"
                    size="small"
                    icon={<CopyOutlined />}
                    onClick={handleCopy}
                  />
                  <Dropdown menu={{ items: actionItems }} trigger={['click']}>
                    <Button type="text" size="small" icon={<MoreOutlined />} />
                  </Dropdown>
                </Space>
              </div>
            )}
          </div>
        </div>
      </Card>

      {/* 修改分类弹窗 */}
      <Modal
        title="修改分类"
        open={categoryModalVisible}
        onOk={handleCategoryChange}
        onCancel={() => setCategoryModalVisible(false)}
        okText="确定"
        cancelText="取消"
      >
        <Select
          value={selectedCategoryId}
          onChange={setSelectedCategoryId}
          style={{ width: '100%' }}
          placeholder="请选择分类"
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
              </Space>
            </Option>
          ))}
        </Select>
      </Modal>

      <style jsx>{`
        .qa-card {
          margin-bottom: 16px;
          transition: all 0.3s ease;
        }
        
        .qa-card:hover {
          box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
        }
        
        .qa-card.compact {
          margin-bottom: 8px;
        }
        
        .qa-content .question-section .question-text {
          font-size: 16px;
          line-height: 1.5;
          display: block;
        }
        
        .qa-content .answer-section .answer-text {
          color: #666;
          line-height: 1.6;
        }
        
        .qa-content .meta-section {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-top: 12px;
          padding-top: 12px;
          border-top: 1px solid #f0f0f0;
        }
        
        .confidence-indicator {
          display: flex;
          align-items: center;
        }
        
        .compact-actions {
          flex-shrink: 0;
        }
        
        @media (max-width: 768px) {
          .qa-content .meta-section {
            flex-direction: column;
            align-items: flex-start;
            gap: 8px;
          }
          
          .compact-actions {
            align-self: flex-end;
          }
        }
      `}</style>
    </>
  )
}

export default QACard