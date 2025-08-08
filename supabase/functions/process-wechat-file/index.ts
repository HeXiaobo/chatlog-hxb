/**
 * Supabase Edge Function: 处理微信聊天记录文件
 * 功能：解析 JSON 文件，提取问答对，自动分类，存储到数据库
 */

import { serve } from "https://deno.land/std@0.168.0/http/server.ts"
import { createClient } from "https://esm.sh/@supabase/supabase-js@2.7.1"

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
  'Access-Control-Allow-Methods': 'POST, GET, OPTIONS',
}

interface WeChatMessage {
  id?: string
  timestamp?: number
  date?: string
  from_user?: string
  content?: string
  message_type?: string
  [key: string]: any
}

interface QAPair {
  question: string
  answer: string
  category_id: number
  asker: string
  advisor: string
  confidence: number
  source_file: string
  original_context?: string
}

serve(async (req) => {
  // 处理预检请求
  if (req.method === 'OPTIONS') {
    return new Response('ok', { headers: corsHeaders })
  }

  try {
    // 初始化 Supabase 客户端
    const supabaseUrl = Deno.env.get('SUPABASE_URL')!
    const supabaseServiceKey = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!
    
    const supabase = createClient(supabaseUrl, supabaseServiceKey)

    if (req.method !== 'POST') {
      throw new Error('只支持 POST 请求')
    }

    const { fileName, fileContent } = await req.json()
    
    if (!fileName || !fileContent) {
      throw new Error('缺少文件名或文件内容')
    }

    console.log(`开始处理文件: ${fileName}`)

    // 解析 JSON 内容
    let messages: WeChatMessage[]
    try {
      const parsedData = typeof fileContent === 'string' 
        ? JSON.parse(fileContent) 
        : fileContent
      
      // 兼容不同的数据结构
      messages = Array.isArray(parsedData) ? parsedData : 
                 parsedData.messages ? parsedData.messages : 
                 parsedData.data ? parsedData.data : []
    } catch (error) {
      throw new Error(`JSON 解析失败: ${error.message}`)
    }

    if (!Array.isArray(messages) || messages.length === 0) {
      throw new Error('文件中没有找到有效的消息数据')
    }

    console.log(`解析到 ${messages.length} 条消息`)

    // 创建上传记录
    const { data: uploadRecord, error: uploadError } = await supabase
      .from('upload_history')
      .insert({
        filename: fileName,
        original_name: fileName,
        file_size: JSON.stringify(fileContent).length,
        status: 'processing',
        total_count: messages.length,
        processed_count: 0
      })
      .select()
      .single()

    if (uploadError) {
      throw new Error(`创建上传记录失败: ${uploadError.message}`)
    }

    // 获取分类映射
    const { data: categories } = await supabase
      .from('categories')
      .select('id, name, description')

    const categoryMap = new Map(categories?.map(cat => [cat.name, cat.id]) || [])

    // 提取问答对
    const qaPairs = extractQAPairs(messages, fileName)
    console.log(`提取到 ${qaPairs.length} 个问答对`)

    // 自动分类并批量插入
    const categorizedPairs = qaPairs.map(pair => ({
      ...pair,
      category_id: categorizeQAPair(pair, categoryMap)
    }))

    // 批量插入问答对
    if (categorizedPairs.length > 0) {
      const { error: insertError } = await supabase
        .from('qa_pairs')
        .insert(categorizedPairs)

      if (insertError) {
        console.error('插入问答对失败:', insertError)
        throw new Error(`插入问答对失败: ${insertError.message}`)
      }
    }

    // 更新上传状态
    await supabase
      .from('upload_history')
      .update({
        status: 'completed',
        processed_count: categorizedPairs.length,
        error_message: null
      })
      .eq('id', uploadRecord.id)

    console.log(`处理完成: 成功插入 ${categorizedPairs.length} 个问答对`)

    return new Response(
      JSON.stringify({
        success: true,
        message: `成功处理文件 ${fileName}`,
        data: {
          upload_id: uploadRecord.id,
          total_messages: messages.length,
          extracted_qa_pairs: categorizedPairs.length,
          processed_count: categorizedPairs.length
        }
      }),
      { 
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
        status: 200 
      }
    )

  } catch (error) {
    console.error('处理文件时出错:', error)
    
    return new Response(
      JSON.stringify({
        success: false,
        error: error.message || '未知错误'
      }),
      { 
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
        status: 400 
      }
    )
  }
})

/**
 * 从微信消息中提取问答对
 */
function extractQAPairs(messages: WeChatMessage[], fileName: string): QAPair[] {
  const qaPairs: QAPair[] = []
  
  for (let i = 0; i < messages.length - 1; i++) {
    const currentMsg = messages[i]
    const nextMsg = messages[i + 1]
    
    // 检查是否可能是问答对
    if (isQuestion(currentMsg) && isAnswer(nextMsg, currentMsg)) {
      // 提取用户名（处理不同的字段名）
      const asker = extractUsername(currentMsg)
      const advisor = extractUsername(nextMsg)
      
      // 跳过同一人的连续消息
      if (asker === advisor) continue
      
      // 计算置信度
      const confidence = calculateConfidence(currentMsg, nextMsg)
      
      // 只保留置信度较高的问答对
      if (confidence >= 0.3) {
        qaPairs.push({
          question: cleanContent(currentMsg.content || ''),
          answer: cleanContent(nextMsg.content || ''),
          category_id: 1, // 默认分类，稍后会重新分类
          asker: asker,
          advisor: advisor,
          confidence: confidence,
          source_file: fileName,
          original_context: JSON.stringify({
            question_msg: currentMsg,
            answer_msg: nextMsg,
            timestamp: currentMsg.timestamp || currentMsg.date
          })
        })
      }
    }
  }
  
  return qaPairs
}

/**
 * 判断是否为问题
 */
function isQuestion(msg: WeChatMessage): boolean {
  const content = msg.content || ''
  
  // 问题特征
  const questionPatterns = [
    /[？?]$/, // 以问号结尾
    /^(请问|咨询|想问|如何|怎么|怎样|为什么|什么|哪里|哪个|多少|几个)/, // 问题开头
    /(怎么办|如何|求助|help|Help)/, // 求助类
    /(可以吗|行吗|好吗|对吗|是吗)$/, // 确认类问题
  ]
  
  return questionPatterns.some(pattern => pattern.test(content)) && 
         content.length >= 5 && content.length <= 200
}

/**
 * 判断是否为回答
 */
function isAnswer(answerMsg: WeChatMessage, questionMsg: WeChatMessage): boolean {
  const content = answerMsg.content || ''
  const questionContent = questionMsg.content || ''
  
  // 回答特征
  const answerPatterns = [
    /^(是的|对的|没错|正确|可以|不可以|建议|推荐)/, // 确认或建议类开头
    /(你可以|您可以|建议您|推荐|方法是|步骤|解决方案)/, // 建议类
    /^(根据|按照|依据)/, // 依据类
  ]
  
  // 检查时间间隔（如果有时间戳）
  const timeGap = getTimeGap(questionMsg, answerMsg)
  const isReasonableTime = timeGap === null || timeGap <= 30 * 60 * 1000 // 30分钟内
  
  return content.length >= 10 && 
         content.length <= 500 && 
         isReasonableTime &&
         (answerPatterns.some(pattern => pattern.test(content)) || 
          content.includes('可以') || 
          content.includes('建议') ||
          hasKeywordOverlap(questionContent, content))
}

/**
 * 提取用户名
 */
function extractUsername(msg: WeChatMessage): string {
  return msg.from_user || msg.sender || msg.user || msg.name || '未知用户'
}

/**
 * 获取时间间隔
 */
function getTimeGap(msg1: WeChatMessage, msg2: WeChatMessage): number | null {
  const time1 = msg1.timestamp || (msg1.date ? new Date(msg1.date).getTime() : null)
  const time2 = msg2.timestamp || (msg2.date ? new Date(msg2.date).getTime() : null)
  
  if (time1 && time2) {
    return Math.abs(time2 - time1)
  }
  
  return null
}

/**
 * 检查关键词重叠
 */
function hasKeywordOverlap(question: string, answer: string): boolean {
  const questionWords = question.replace(/[^\u4e00-\u9fa5a-zA-Z0-9]/g, '').split('')
  const answerWords = answer.replace(/[^\u4e00-\u9fa5a-zA-Z0-9]/g, '').split('')
  
  const overlap = questionWords.filter(word => answerWords.includes(word))
  return overlap.length >= 2
}

/**
 * 计算置信度
 */
function calculateConfidence(questionMsg: WeChatMessage, answerMsg: WeChatMessage): number {
  let confidence = 0.5 // 基础置信度
  
  const question = questionMsg.content || ''
  const answer = answerMsg.content || ''
  
  // 问号加分
  if (question.includes('？') || question.includes('?')) confidence += 0.2
  
  // 长度合理加分
  if (answer.length >= 20 && answer.length <= 300) confidence += 0.1
  
  // 时间间隔合理加分
  const timeGap = getTimeGap(questionMsg, answerMsg)
  if (timeGap && timeGap <= 5 * 60 * 1000) confidence += 0.1 // 5分钟内回复
  
  // 关键词匹配加分
  if (hasKeywordOverlap(question, answer)) confidence += 0.1
  
  return Math.min(confidence, 1.0)
}

/**
 * 清理内容
 */
function cleanContent(content: string): string {
  return content
    .replace(/^\s+|\s+$/g, '') // 去除首尾空白
    .replace(/\n+/g, ' ') // 替换换行为空格
    .replace(/\s+/g, ' ') // 合并多个空格
    .substring(0, 1000) // 限制长度
}

/**
 * 自动分类问答对
 */
function categorizeQAPair(pair: QAPair, categoryMap: Map<string, number>): number {
  const content = (pair.question + ' ' + pair.answer).toLowerCase()
  
  // 分类关键词映射
  const categoryKeywords = {
    '产品咨询': ['产品', '功能', '特性', '介绍', '什么是', '用途', '作用'],
    '技术支持': ['错误', '故障', '问题', '不能', '无法', '失败', '异常', '技术'],
    '价格费用': ['价格', '费用', '多少钱', '成本', '收费', '付费', '免费'],
    '使用教程': ['怎么', '如何', '教程', '步骤', '方法', '操作', '使用'],
    '售后问题': ['退款', '退货', '售后', '服务', '保修', '维修', '客服']
  }
  
  let maxScore = 0
  let bestCategory = 1 // 默认为产品咨询
  
  for (const [categoryName, keywords] of Object.entries(categoryKeywords)) {
    const categoryId = categoryMap.get(categoryName)
    if (!categoryId) continue
    
    let score = 0
    for (const keyword of keywords) {
      if (content.includes(keyword)) {
        score += 1
      }
    }
    
    if (score > maxScore) {
      maxScore = score
      bestCategory = categoryId
    }
  }
  
  return bestCategory
}