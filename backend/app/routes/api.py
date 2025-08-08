"""
API基础路由
"""
from flask import Blueprint, jsonify, request
from datetime import datetime
from app import db
from app.models import Category, QAPair

api_bp = Blueprint('api', __name__)


@api_bp.route('/health')
def health_check():
    """系统健康检查"""
    return jsonify({
        'success': True,
        'data': {
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'version': '1.0.0'
        },
        'message': '系统运行正常'
    })


@api_bp.route('/info')
def api_info():
    """API信息"""
    return jsonify({
        'success': True,
        'data': {
            'name': 'Chatlog Knowledge Base API',
            'version': '1.0.0',
            'description': '微信群问答知识库API',
            'endpoints': {
                'upload': '/api/v1/upload/*',
                'search': '/api/v1/search/*',
                'qa': '/api/v1/qa/*',
                'categories': '/api/v1/categories/*',
                'admin': '/api/v1/admin/*'
            }
        },
        'message': 'API信息获取成功'
    })


@api_bp.route('/categories')
def get_categories():
    """获取所有分类"""
    try:
        categories = Category.query.all()
        return jsonify({
            'success': True,
            'data': [cat.to_dict() for cat in categories],
            'message': '分类获取成功'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': {
                'code': 'DATABASE_ERROR',
                'message': '获取分类失败',
                'details': str(e)
            }
        }), 500


@api_bp.route('/qa')
def get_qa_pairs():
    """获取问答对列表"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        limit = request.args.get('limit', type=int)
        confidence_min = request.args.get('confidence_min', type=float)
        
        query = QAPair.query
        
        # 添加置信度过滤
        if confidence_min is not None:
            query = query.filter(QAPair.confidence >= confidence_min)
            
        query = query.order_by(QAPair.created_at.desc())
        
        if limit:
            qas = query.limit(limit).all()
            return jsonify({
                'success': True,
                'data': [qa.to_dict(include_relationships=True) for qa in qas],
                'total': query.count(),
                'message': '问答获取成功'
            })
        else:
            pagination = query.paginate(
                page=page, 
                per_page=min(per_page, 100),
                error_out=False
            )
            
            return jsonify({
                'success': True,
                'data': [qa.to_dict(include_relationships=True) for qa in pagination.items],
                'pagination': {
                    'page': pagination.page,
                    'per_page': pagination.per_page,
                    'total': pagination.total,
                    'pages': pagination.pages
                },
                'total': pagination.total,
                'message': '问答获取成功'
            })
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': {
                'code': 'DATABASE_ERROR', 
                'message': '获取问答失败',
                'details': str(e)
            }
        }), 500


@api_bp.route('/qa/<int:qa_id>')
def get_qa_detail(qa_id):
    """获取问答详情"""
    try:
        qa = QAPair.query.get_or_404(qa_id)
        return jsonify({
            'success': True,
            'data': qa.to_dict(include_relationships=True),
            'message': '问答详情获取成功'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': {
                'code': 'NOT_FOUND',
                'message': '问答不存在',
                'details': str(e)
            }
        }), 404