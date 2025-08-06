import { createClient } from '@supabase/supabase-js'
import { config } from 'dotenv'
import fetch from 'node-fetch'

// 加载环境变量
config({ path: './frontend/.env.development' })

const supabaseUrl = process.env.VITE_SUPABASE_URL
const supabaseAnonKey = process.env.VITE_SUPABASE_ANON_KEY

console.log('🔍 详细诊断 Supabase 连接...')
console.log(`URL: ${supabaseUrl}`)
console.log(`Key: ${supabaseAnonKey ? supabaseAnonKey.substring(0, 30) + '...' : 'NOT_SET'}`)

async function diagnose() {
    try {
        // 测试 1: 基础网络连接
        console.log('\n1️⃣ 测试基础网络连接...')
        const healthUrl = `${supabaseUrl}/rest/v1/`
        
        console.log(`   正在连接: ${healthUrl}`)
        const response = await fetch(healthUrl, {
            method: 'HEAD',
            headers: {
                'apikey': supabaseAnonKey,
                'Authorization': `Bearer ${supabaseAnonKey}`
            }
        })
        
        console.log(`   HTTP 状态: ${response.status} ${response.statusText}`)
        
        if (response.status === 200) {
            console.log('   ✅ 基础连接成功')
        } else {
            console.log('   ❌ 基础连接失败')
            return
        }

        // 测试 2: Supabase 客户端连接
        console.log('\n2️⃣ 测试 Supabase 客户端...')
        const supabase = createClient(supabaseUrl, supabaseAnonKey)
        
        // 简单的查询测试
        const { data, error } = await supabase
            .from('categories')
            .select('count')
            .limit(1)
            .maybeSingle()

        if (error) {
            console.log(`   ❌ 客户端连接失败: ${error.message}`)
            console.log(`   错误详情: ${JSON.stringify(error, null, 2)}`)
            
            // 检查是否是权限问题
            if (error.message.includes('permission') || error.message.includes('RLS')) {
                console.log('\n🛠️ 可能是权限配置问题:')
                console.log('   请检查是否正确执行了 03_rls_policies.sql')
            }
        } else {
            console.log('   ✅ Supabase 客户端连接成功')
            
            // 测试 3: 检查表是否存在
            console.log('\n3️⃣ 检查数据库表...')
            const { data: tables, error: tablesError } = await supabase
                .from('information_schema.tables')
                .select('table_name')
                .eq('table_schema', 'public')
                .in('table_name', ['categories', 'qa_pairs', 'upload_history'])

            if (tablesError) {
                console.log(`   ❌ 无法查询表信息: ${tablesError.message}`)
            } else {
                console.log(`   ✅ 找到表: ${tables.map(t => t.table_name).join(', ')}`)
                
                if (tables.length < 3) {
                    console.log('   ⚠️ 缺少表，请检查是否正确执行了 01_schema.sql')
                }
            }
        }

    } catch (error) {
        console.log(`\n❌ 诊断过程中出错: ${error.message}`)
        console.log('错误堆栈:', error.stack)
        
        if (error.code === 'ENOTFOUND') {
            console.log('\n🛠️ DNS 解析失败:')
            console.log('   1. 检查网络连接')
            console.log('   2. 检查 Supabase URL 是否正确')
            console.log('   3. 尝试在浏览器中访问 Supabase 项目仪表板')
        }
        
        if (error.code === 'ECONNREFUSED') {
            console.log('\n🛠️ 连接被拒绝:')
            console.log('   1. 检查 Supabase 项目是否正常运行')
            console.log('   2. 检查防火墙设置')
        }
    }
}

diagnose()