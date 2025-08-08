#!/usr/bin/env python3
"""
测试Kimi API配置脚本
"""
import sys
import os

# 添加backend路径
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from app.services.ai_config import ai_config_manager, AIProvider

def test_kimi_configuration():
    """测试Kimi配置"""
    print("🌙 测试月之暗面Kimi API配置...")
    print("=" * 50)
    
    # 检查Kimi配置是否存在
    kimi_config = ai_config_manager.get_model_config(AIProvider.KIMI.value)
    if not kimi_config:
        print("❌ Kimi配置不存在")
        print("请确保已经通过AI管理页面或环境变量添加了Kimi配置")
        return False
    
    print(f"✅ 找到Kimi配置:")
    print(f"   提供商: {kimi_config.provider}")
    print(f"   模型: {kimi_config.model_name}")
    print(f"   API Base: {kimi_config.api_base}")
    print(f"   启用状态: {kimi_config.enabled}")
    print(f"   每日限额: {kimi_config.daily_limit}")
    print(f"   Token成本: ${kimi_config.cost_per_1k_tokens}/1K tokens")
    
    if not kimi_config.api_key:
        print("⚠️  API Key未配置")
        return False
    
    print(f"   API Key: {kimi_config.api_key[:10]}...{kimi_config.api_key[-4:]} (部分显示)")
    print()
    
    # 测试连接
    print("🔧 开始连接测试...")
    result = ai_config_manager.test_provider_connection(AIProvider.KIMI.value)
    
    if result['success']:
        print("✅ 连接测试成功!")
        print(f"   响应时间: {result.get('response_time', 'N/A')}秒")
        if 'response_content' in result:
            print(f"   API响应: {result['response_content']}")
        print(f"   消息: {result['message']}")
    else:
        print("❌ 连接测试失败!")
        print(f"   错误信息: {result['error']}")
        return False
    
    print()
    return True

def test_ai_system_status():
    """测试AI系统整体状态"""
    print("🤖 检查AI系统整体状态...")
    print("=" * 50)
    
    # 获取可用的提供商
    available_providers = ai_config_manager.get_available_providers()
    print(f"✅ 可用的AI提供商 ({len(available_providers)}个):")
    for provider in available_providers:
        config = ai_config_manager.get_model_config(provider)
        status = "🟢" if config.enabled else "🔴"
        print(f"   {status} {provider} ({config.model_name})")
    
    # 获取主提供商
    primary_provider = ai_config_manager.get_primary_provider()
    print(f"\n🎯 主提供商: {primary_provider}")
    
    # 检查使用统计
    usage_summary = ai_config_manager.get_usage_summary()
    print(f"\n📊 使用统计:")
    print(f"   总请求数: {usage_summary['total_requests']}")
    print(f"   总成本: ${usage_summary['total_cost']}")
    print(f"   总Token: {usage_summary['total_tokens']}")
    
    if AIProvider.KIMI.value in usage_summary['providers']:
        kimi_stats = usage_summary['providers'][AIProvider.KIMI.value]
        print(f"\n🌙 Kimi使用统计:")
        print(f"   请求数: {kimi_stats['requests']}")
        print(f"   成功率: {kimi_stats['success_rate']:.1f}%")
        print(f"   Token使用: {kimi_stats['tokens_used']}")
        print(f"   成本: ${kimi_stats['cost']}")
        print(f"   今日使用: {kimi_stats['daily_usage']['requests']}次请求")
    
    print()

def main():
    """主函数"""
    print("🚀 ChatLog AI系统测试工具")
    print("=" * 50)
    
    try:
        # 测试AI系统状态
        test_ai_system_status()
        
        # 测试Kimi配置
        if test_kimi_configuration():
            print("🎉 Kimi API配置测试通过!")
            print("\n✨ 接下来你可以:")
            print("   1. 在AI管理页面查看详细状态")
            print("   2. 在文件上传时选择AI智能处理")
            print("   3. 体验AI增强的数据提取和分类")
        else:
            print("💡 建议检查:")
            print("   1. API Key是否正确")
            print("   2. 网络连接是否正常")
            print("   3. Kimi账户余额是否充足")
            return 1
        
    except Exception as e:
        print(f"❌ 测试过程中发生错误: {str(e)}")
        import traceback
        print("\n详细错误信息:")
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())