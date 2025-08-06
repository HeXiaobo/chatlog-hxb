#!/usr/bin/env python3
"""
开发环境启动脚本
微信群问答知识库系统

使用方法:
    python run_dev.py              # 启动开发服务器
    python run_dev.py --setup      # 初始化数据库和环境
    python run_dev.py --reset      # 重置数据库
    python run_dev.py --test       # 运行测试
"""

import os
import sys
import argparse
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def setup_environment():
    """设置开发环境"""
    print("🔧 设置开发环境...")
    
    # 创建必要的目录
    directories = [
        'logs',
        'uploads', 
        'data',
        'migrations/versions'
    ]
    
    for directory in directories:
        dir_path = project_root / directory
        dir_path.mkdir(exist_ok=True)
        print(f"✅ 创建目录: {directory}")
    
    # 检查Python依赖
    print("\n📦 检查Python依赖...")
    try:
        import flask
        import flask_sqlalchemy
        import flask_migrate
        import flask_cors
        import jieba
        print("✅ 所有必需依赖已安装")
    except ImportError as e:
        print(f"❌ 缺少依赖: {e}")
        print("请运行: pip install -r requirements.txt")
        return False
    
    return True

def initialize_database():
    """初始化数据库"""
    print("\n🗃️ 初始化数据库...")
    
    try:
        from app import create_app, db
        from app.models import Category, QAPair, UploadHistory
        
        app = create_app()
        
        with app.app_context():
            # 创建所有表
            print("创建数据库表...")
            db.create_all()
            
            # 检查是否已有默认分类
            existing_categories = Category.query.count()
            if existing_categories == 0:
                print("添加默认分类...")
                default_categories = [
                    {'name': '产品咨询', 'description': '关于产品功能和特性的问题', 'color': '#1890ff'},
                    {'name': '技术支持', 'description': '技术问题和故障排除', 'color': '#f5222d'},
                    {'name': '价格费用', 'description': '价格、费用相关问题', 'color': '#52c41a'},
                    {'name': '使用教程', 'description': '操作指南和使用方法', 'color': '#faad14'},
                    {'name': '售后问题', 'description': '售后服务相关问题', 'color': '#722ed1'},
                ]
                
                for cat_data in default_categories:
                    category = Category(**cat_data)
                    db.session.add(category)
                
                db.session.commit()
                print(f"✅ 添加了 {len(default_categories)} 个默认分类")
            else:
                print(f"✅ 数据库已初始化，存在 {existing_categories} 个分类")
            
            # 创建示例数据（可选）
            qa_count = QAPair.query.count()
            if qa_count == 0:
                print("创建示例问答数据...")
                create_sample_data()
            
            print("✅ 数据库初始化完成")
            return True
            
    except Exception as e:
        print(f"❌ 数据库初始化失败: {str(e)}")
        return False

def create_sample_data():
    """创建示例数据"""
    from app import db
    from app.models import QAPair, Category
    from datetime import datetime
    
    # 示例问答数据
    sample_data = [
        {
            'question': '如何使用chatlog导出微信群记录？',
            'answer': '您可以使用以下命令：chatlog export --platform wechat --group-name "群名称" --output wechat_data.json',
            'category_name': '使用教程',
            'advisor': '技术支持',
            'confidence': 0.9
        },
        {
            'question': '支持哪些聊天平台的数据导出？',
            'answer': 'chatlog工具目前支持微信和QQ平台的聊天记录导出，未来会支持更多平台',
            'category_name': '产品咨询',
            'advisor': '产品经理',
            'confidence': 0.85
        },
        {
            'question': '上传的JSON文件格式有什么要求？',
            'answer': '支持标准的WeChat导出JSON格式，文件大小不超过50MB，编码格式为UTF-8',
            'category_name': '技术支持',
            'advisor': '技术支持',
            'confidence': 0.8
        },
        {
            'question': '知识库搜索支持中文吗？',
            'answer': '是的，系统支持中文全文搜索，使用了jieba分词和FTS5索引技术，搜索效果很好',
            'category_name': '产品咨询',
            'advisor': '产品经理',
            'confidence': 0.9
        }
    ]
    
    for item in sample_data:
        category = Category.query.filter_by(name=item['category_name']).first()
        if category:
            qa = QAPair(
                question=item['question'],
                answer=item['answer'],
                category_id=category.id,
                advisor=item['advisor'],
                confidence=item['confidence'],
                source_file='sample_data'
            )
            db.session.add(qa)
    
    db.session.commit()
    print(f"✅ 创建了 {len(sample_data)} 个示例问答")

def reset_database():
    """重置数据库"""
    print("🗑️ 重置数据库...")
    
    try:
        from app import create_app, db
        
        app = create_app()
        
        with app.app_context():
            # 删除所有表
            db.drop_all()
            print("✅ 删除了所有数据库表")
            
            # 重新创建
            return initialize_database()
            
    except Exception as e:
        print(f"❌ 重置数据库失败: {str(e)}")
        return False

def run_tests():
    """运行测试"""
    print("🧪 运行测试...")
    
    # 检查是否有测试文件
    test_dir = project_root / 'tests'
    if not test_dir.exists():
        print("⚠️ 未找到tests目录，跳过测试")
        return True
    
    try:
        import pytest
        exit_code = pytest.main([str(test_dir), '-v'])
        if exit_code == 0:
            print("✅ 所有测试通过")
            return True
        else:
            print("❌ 测试失败")
            return False
    except ImportError:
        print("⚠️ pytest未安装，跳过测试")
        return True
    except Exception as e:
        print(f"❌ 测试运行失败: {str(e)}")
        return False

def start_dev_server():
    """启动开发服务器"""
    print("🚀 启动开发服务器...")
    
    try:
        from app import create_app
        
        app = create_app()
        
        print("\n" + "="*50)
        print("🎉 微信群问答知识库系统")
        print("📍 开发服务器地址: http://localhost:5000")
        print("📖 API文档: http://localhost:5000/api/v1/info")
        print("💡 健康检查: http://localhost:5000/api/v1/health")
        print("="*50 + "\n")
        
        # 启动开发服务器
        app.run(
            host='0.0.0.0',
            port=5000,
            debug=True,
            use_reloader=True
        )
        
    except Exception as e:
        print(f"❌ 启动开发服务器失败: {str(e)}")
        return False

def check_system():
    """系统检查"""
    print("🔍 系统检查...")
    
    issues = []
    
    # 检查Python版本
    python_version = sys.version_info
    if python_version < (3, 7):
        issues.append(f"Python版本过低: {python_version.major}.{python_version.minor}, 需要3.7+")
    else:
        print(f"✅ Python版本: {python_version.major}.{python_version.minor}.{python_version.micro}")
    
    # 检查数据库文件
    db_file = project_root / 'chatlog_dev.db'
    if db_file.exists():
        print(f"✅ 数据库文件存在: {db_file}")
    else:
        print(f"⚠️ 数据库文件不存在: {db_file}")
    
    # 检查配置文件
    config_file = project_root / 'config.py'
    if config_file.exists():
        print(f"✅ 配置文件存在: {config_file}")
    else:
        issues.append(f"配置文件不存在: {config_file}")
    
    # 检查关键目录
    key_dirs = ['logs', 'uploads']
    for dir_name in key_dirs:
        dir_path = project_root / dir_name
        if dir_path.exists():
            print(f"✅ 目录存在: {dir_name}")
        else:
            print(f"⚠️ 目录不存在: {dir_name} (将自动创建)")
    
    if issues:
        print(f"\n❌ 发现 {len(issues)} 个问题:")
        for issue in issues:
            print(f"  - {issue}")
        return False
    else:
        print("\n✅ 系统检查通过")
        return True

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='微信群问答知识库系统开发工具')
    parser.add_argument('--setup', action='store_true', help='初始化环境和数据库')
    parser.add_argument('--reset', action='store_true', help='重置数据库')
    parser.add_argument('--test', action='store_true', help='运行测试')
    parser.add_argument('--check', action='store_true', help='系统检查')
    
    args = parser.parse_args()
    
    print("🎯 微信群问答知识库系统 - 开发工具")
    print("="*50)
    
    if args.setup:
        success = setup_environment() and initialize_database()
        if success:
            print("\n🎉 环境设置完成！现在可以运行: python run_dev.py")
        else:
            sys.exit(1)
    elif args.reset:
        success = reset_database()
        if not success:
            sys.exit(1)
    elif args.test:
        success = run_tests()
        if not success:
            sys.exit(1)
    elif args.check:
        success = check_system()
        if not success:
            sys.exit(1)
    else:
        # 默认行为：检查系统并启动服务器
        if check_system():
            start_dev_server()
        else:
            print("\n💡 提示: 运行 'python run_dev.py --setup' 来修复问题")
            sys.exit(1)

if __name__ == '__main__':
    main()