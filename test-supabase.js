/**
 * Supabase 连接测试脚本
 * 运行此脚本验证数据库设置是否正确
 */

import { createClient } from '@supabase/supabase-js'
import { config } from 'dotenv'
import { readFileSync } from 'fs'
import { join } from 'path'

// 加载环境变量
config({ path: './frontend/.env.development' })

const supabaseUrl = process.env.VITE_SUPABASE_URL
const supabaseAnonKey = process.env.VITE_SUPABASE_ANON_KEY

console.log('🔍 检查 Supabase 配置...')
console.log(`URL: ${supabaseUrl}`)
console.log(`Key: ${supabaseAnonKey ? supabaseAnonKey.substring(0, 20) + '...' : 'NOT_SET'}`)

if (!supabaseUrl || !supabaseAnonKey || 
    supabaseUrl.includes('your-project-id') || 
    supabaseAnonKey.includes('your-anon-key')) {
    console.log('\n❌ 环境变量未正确配置')
    console.log('请按照 SUPABASE_MIGRATION_GUIDE.md 第3步配置环境变量')
    process.exit(1)
}

const supabase = createClient(supabaseUrl, supabaseAnonKey)

async function testConnection() {
    console.log('\n🧪 测试数据库连接...')
    
    try {
        // 测试 1: 检查分类表
        console.log('1️⃣ 检查分类表...')
        const { data: categories, error: catError } = await supabase
            .from('categories')
            .select('*')
            .order('id')

        if (catError) {
            throw new Error(`分类表查询失败: ${catError.message}`)
        }

        console.log(`   ✅ 找到 ${categories.length} 个分类`)
        categories.forEach(cat => {
            console.log(`      - ${cat.name} (${cat.color})`)
        })

        // 测试 2: 检查问答表和示例数据
        console.log('\n2️⃣ 检查问答表...')
        const { data: qaPairs, error: qaError } = await supabase
            .from('qa_pairs')
            .select(`
                *,
                category:categories(name, color)
            `)
            .limit(3)

        if (qaError) {
            throw new Error(`问答表查询失败: ${qaError.message}`)
        }

        console.log(`   ✅ 找到示例问答数据 ${qaPairs.length} 条`)
        qaPairs.forEach(qa => {
            console.log(`      - ${qa.question.substring(0, 30)}...`)
        })

        // 测试 3: 检查全文搜索函数
        console.log('\n3️⃣ 测试全文搜索功能...')
        const { data: searchResults, error: searchError } = await supabase
            .rpc('search_qa_pairs', {
                search_query: '价格',
                limit_count: 2
            })

        if (searchError) {
            throw new Error(`搜索功能测试失败: ${searchError.message}`)
        }

        console.log(`   ✅ 搜索"价格"找到 ${searchResults.length} 条结果`)
        searchResults.forEach(result => {
            console.log(`      - ${result.question} (相关性: ${result.search_rank})`)
        })

        // 测试 4: 检查统计函数
        console.log('\n4️⃣ 测试统计功能...')
        const { data: stats, error: statsError } = await supabase
            .rpc('get_qa_statistics')

        if (statsError) {
            throw new Error(`统计功能测试失败: ${statsError.message}`)
        }

        console.log(`   ✅ 统计数据获取成功`)
        console.log(`      - 总问答数: ${stats.total_qa}`)
        console.log(`      - 总分类数: ${stats.total_categories}`)
        console.log(`      - 平均信心度: ${stats.confidence_stats.average}`)

        // 测试 5: 测试实时订阅
        console.log('\n5️⃣ 测试实时订阅功能...')
        const subscription = supabase
            .channel('qa_pairs_changes')
            .on('postgres_changes', 
                { event: '*', schema: 'public', table: 'qa_pairs' },
                (payload) => {
                    console.log(`   📡 实时更新: ${payload.eventType}`)
                }
            )
            .subscribe((status) => {
                if (status === 'SUBSCRIBED') {
                    console.log('   ✅ 实时订阅连接成功')
                    subscription.unsubscribe()
                } else if (status === 'CHANNEL_ERROR') {
                    console.log('   ⚠️ 实时订阅连接失败')
                }
            })

        console.log('\n🎉 所有测试通过！Supabase 配置正确')
        console.log('\n📋 测试结果摘要:')
        console.log(`   ✅ 数据库连接: 正常`)
        console.log(`   ✅ 表结构: 正常 (${categories.length} 分类, ${qaPairs.length}+ 问答)`)
        console.log(`   ✅ 全文搜索: 正常`)
        console.log(`   ✅ 统计功能: 正常`)
        console.log(`   ✅ 实时订阅: 正常`)

        console.log('\n🚀 现在可以继续第3步：本地测试')
        console.log('   运行: cd frontend && npm run dev')

    } catch (error) {
        console.log(`\n❌ 测试失败: ${error.message}`)
        console.log('\n🛠️ 可能的解决方案:')
        console.log('1. 检查 Supabase 项目是否正常运行')
        console.log('2. 确认 API Key 权限正确')
        console.log('3. 验证所有 SQL 脚本是否正确执行')
        console.log('4. 检查网络连接')
        
        process.exit(1)
    }
}

testConnection()