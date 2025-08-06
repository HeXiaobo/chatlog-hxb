"""
Flask应用工厂模式
"""
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_cors import CORS

# 初始化扩展
db = SQLAlchemy()
migrate = Migrate()
cors = CORS()


def create_app(config_object=None):
    """
    Flask应用工厂函数
    
    Args:
        config_object: 配置对象，如果为None则从环境变量获取
    
    Returns:
        Flask: 配置好的Flask应用实例
    """
    app = Flask(__name__)
    
    # 加载配置
    if config_object is None:
        from config import get_config
        config_class = get_config()
    else:
        config_class = config_object
    
    app.config.from_object(config_class)
    
    # 初始化扩展
    db.init_app(app)
    migrate.init_app(app, db)
    cors.init_app(app)
    
    # 初始化配置
    config_class.init_app(app)
    
    # 注册蓝图
    register_blueprints(app)
    
    # 注册错误处理
    register_error_handlers(app)
    
    # 注册CLI命令
    register_cli_commands(app)
    
    return app


def register_blueprints(app):
    """注册蓝图"""
    from app.routes.api import api_bp
    from app.routes.upload import upload_bp
    from app.routes.search import search_bp
    from app.routes.admin import admin_bp
    
    # API路由
    app.register_blueprint(api_bp, url_prefix='/api/v1')
    app.register_blueprint(upload_bp, url_prefix='/api/v1/upload')
    app.register_blueprint(search_bp, url_prefix='/api/v1/search')
    app.register_blueprint(admin_bp, url_prefix='/api/v1/admin')


def register_error_handlers(app):
    """注册错误处理器"""
    from werkzeug.exceptions import HTTPException
    from flask import jsonify
    
    @app.errorhandler(400)
    def bad_request(error):
        return jsonify({
            'success': False,
            'error': {
                'code': 'BAD_REQUEST',
                'message': '请求参数错误',
                'details': str(error.description)
            },
            'timestamp': app.config.get('TIMESTAMP_FORMAT', '%Y-%m-%d %H:%M:%S')
        }), 400
    
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({
            'success': False,
            'error': {
                'code': 'NOT_FOUND',
                'message': '资源不存在',
                'details': str(error.description)
            }
        }), 404
    
    @app.errorhandler(413)
    def request_entity_too_large(error):
        return jsonify({
            'success': False,
            'error': {
                'code': 'FILE_TOO_LARGE',
                'message': '上传文件过大',
                'details': f'文件大小不能超过{app.config["MAX_CONTENT_LENGTH"] // (1024*1024)}MB'
            }
        }), 413
    
    @app.errorhandler(422)
    def unprocessable_entity(error):
        return jsonify({
            'success': False,
            'error': {
                'code': 'VALIDATION_ERROR',
                'message': '数据验证失败',
                'details': str(error.description)
            }
        }), 422
    
    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': {
                'code': 'INTERNAL_SERVER_ERROR',
                'message': '服务器内部错误',
                'details': 'An internal error occurred'
            }
        }), 500
    
    @app.errorhandler(HTTPException)
    def handle_http_exception(error):
        return jsonify({
            'success': False,
            'error': {
                'code': error.name.upper().replace(' ', '_'),
                'message': error.description,
                'details': str(error)
            }
        }), error.code


def register_cli_commands(app):
    """注册CLI命令"""
    
    @app.cli.command()
    def init_db():
        """初始化数据库"""
        from flask import current_app
        from app.models import Category
        
        # 创建表
        db.create_all()
        
        # 创建默认分类
        categories = [
            {'name': '产品咨询', 'description': '关于产品功能和特性的问题', 'color': '#1890ff'},
            {'name': '技术支持', 'description': '技术问题和故障排除', 'color': '#f5222d'},
            {'name': '价格费用', 'description': '价格、费用相关问题', 'color': '#52c41a'},
            {'name': '使用教程', 'description': '操作指南和使用方法', 'color': '#faad14'},
            {'name': '售后问题', 'description': '售后服务相关问题', 'color': '#722ed1'},
        ]
        
        for cat_data in categories:
            if not Category.query.filter_by(name=cat_data['name']).first():
                category = Category(**cat_data)
                db.session.add(category)
        
        db.session.commit()
        current_app.logger.info('Database initialized successfully')
    
    @app.cli.command()
    def reset_db():
        """重置数据库"""
        from flask import current_app
        db.drop_all()
        db.create_all()
        current_app.logger.info('Database reset successfully')
    
    @app.cli.command()
    def create_sample_data():
        """创建示例数据"""
        from app.models import QAPair, Category
        import json
        from datetime import datetime
        
        # 创建示例问答数据
        sample_data = [
            {
                'question': '如何使用chatlog导出微信群记录？',
                'answer': '您可以使用以下命令：chatlog export --platform wechat --output wechat_data.json',
                'category_name': '使用教程',
                'advisor': '技术支持',
                'confidence': 0.9
            },
            {
                'question': '支持哪些聊天平台的数据导出？',
                'answer': 'chatlog工具目前支持微信和QQ平台的聊天记录导出',
                'category_name': '产品咨询',
                'advisor': '产品经理',
                'confidence': 0.85
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
                    confidence=item['confidence']
                )
                db.session.add(qa)
        
        db.session.commit()
        app.logger.info('Sample data created successfully')