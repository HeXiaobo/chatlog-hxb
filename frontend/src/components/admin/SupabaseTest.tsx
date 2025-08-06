import React, { useState } from 'react'
import { Card, Button, Alert, Space } from 'antd'
import { PlayCircleOutlined, ReloadOutlined } from '@ant-design/icons'
import { testSupabaseConnection, supabase } from '../../lib/supabase'

const SupabaseTest: React.FC = () => {
  const [isRunning, setIsRunning] = useState(false)
  const [testResults, setTestResults] = useState<string[]>([])
  const [hasError, setHasError] = useState(false)

  const addResult = (message: string, isError = false) => {
    setTestResults(prev => [...prev, (isError ? '❌ ' : '✅ ') + message])
    if (isError) setHasError(true)
  }

  const runTests = async () => {
    setIsRunning(true)
    setTestResults([])
    setHasError(false)

    try {
      // 测试 1: 基础连接
      addResult('开始测试 Supabase 连接...')
      
      const isConnected = await testSupabaseConnection()
      if (!isConnected) {
        addResult('Supabase 连接失败，请检查环境变量配置', true)
        return
      }
      addResult('Supabase 基础连接成功')

      // 测试 2: 分类表查询
      addResult('测试分类表查询...')
      const { data: categories, error: catError } = await supabase
        .from('categories')
        .select('*')
        .limit(5)
      
      if (catError) {
        addResult(`分类表查询失败: ${catError.message}`, true)
      } else {
        addResult(`分类表查询成功，找到 ${categories.length} 个分类`)
      }

      // 测试 3: 问答表查询
      addResult('测试问答表查询...')
      const { data: qaPairs, error: qaError } = await supabase
        .from('qa_pairs')
        .select('id, question')
        .limit(3)
      
      if (qaError) {
        addResult(`问答表查询失败: ${qaError.message}`, true)
      } else {
        addResult(`问答表查询成功，找到 ${qaPairs.length} 条记录`)
      }

      // 测试 4: 简单搜索功能（不使用自定义函数）
      addResult('测试基础搜索功能...')
      const { data: searchResults, error: searchError } = await supabase
        .from('qa_pairs')
        .select(`
          id, question, answer,
          category:categories(name, color)
        `)
        .textSearch('fts_vector', '价格')
        .limit(1)
      
      if (searchError) {
        addResult(`基础搜索测试失败: ${searchError.message}`, true)
      } else {
        addResult(`基础搜索正常，找到 ${searchResults.length} 条结果`)
      }

      // 测试 5: 基础统计（不使用自定义函数）
      addResult('测试基础统计功能...')
      
      // 简单统计查询
      const { count: totalQA, error: countError } = await supabase
        .from('qa_pairs')
        .select('*', { count: 'exact', head: true })
      
      if (countError) {
        addResult(`统计测试失败: ${countError.message}`, true)
      } else {
        addResult(`基础统计正常，总问答数: ${totalQA}`)
      }

      if (!hasError) {
        addResult('🎉 所有测试通过！Supabase 配置正确')
      }

    } catch (error: any) {
      addResult(`测试过程中出错: ${error.message}`, true)
    } finally {
      setIsRunning(false)
    }
  }

  return (
    <Card title="🧪 Supabase 连接测试" style={{ marginBottom: 24 }}>
      <Space direction="vertical" style={{ width: '100%' }}>
        <Space>
          <Button 
            type="primary" 
            icon={<PlayCircleOutlined />}
            onClick={runTests}
            loading={isRunning}
          >
            开始测试
          </Button>
          <Button 
            icon={<ReloadOutlined />}
            onClick={() => {
              setTestResults([])
              setHasError(false)
            }}
            disabled={isRunning}
          >
            清除结果
          </Button>
        </Space>

        {testResults.length > 0 && (
          <Alert
            message="测试结果"
            description={
              <div>
                {testResults.map((result, index) => (
                  <div key={index} style={{ marginBottom: 4 }}>
                    {result}
                  </div>
                ))}
              </div>
            }
            type={hasError ? 'error' : 'success'}
            showIcon
          />
        )}

        {testResults.length === 0 && (
          <Alert
            message='点击"开始测试"按钮来验证您的 Supabase 配置'
            type="info"
            showIcon
          />
        )}
      </Space>
    </Card>
  )
}

export default SupabaseTest