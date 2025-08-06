"""
搜索相关路由
"""
import logging
from flask import Blueprint, jsonify, request
from app.services.search_service import SearchService

logger = logging.getLogger(__name__)
search_bp = Blueprint('search', __name__)


@search_bp.route('/')
def search_qa():
    """搜索问答"""
    try:
        # 获取查询参数
        query = request.args.get('q', '').strip()
        category_ids = []
        if request.args.get('category'):
            try:
                category_ids = [int(request.args.get('category'))]
            except ValueError:
                pass
        
        advisor = request.args.get('advisor', '').strip() or None
        page = max(1, request.args.get('page', 1, type=int))
        per_page = min(max(1, request.args.get('per_page', 20, type=int)), 100)
        sort_by = request.args.get('sort_by', 'relevance')
        
        # 验证排序参数
        if sort_by not in ['relevance', 'time', 'confidence']:
            sort_by = 'relevance'
        
        # 执行搜索
        search_service = SearchService()
        result = search_service.search(
            query=query,
            category_ids=category_ids,
            advisor=advisor,
            page=page,
            per_page=per_page,
            sort_by=sort_by
        )
        
        return jsonify({
            'success': True,
            'data': [qa.to_dict(include_relationships=True, highlight_query=query) 
                    for qa in result.qa_pairs],
            'pagination': {
                'page': result.page,
                'per_page': result.per_page,
                'total': result.total_count,
                'pages': result.pages
            },
            'search_info': {
                'query': result.query,
                'search_time': round(result.search_time, 3),
                'sort_by': sort_by,
                'category_ids': category_ids,
                'advisor': advisor
            },
            'suggestions': result.suggestions,
            'message': f'找到 {result.total_count} 条相关结果'
        })
        
    except Exception as e:
        logger.error(f"Search error: {str(e)}")
        return jsonify({
            'success': False,
            'error': {
                'code': 'SEARCH_ERROR',
                'message': '搜索失败',
                'details': str(e)
            }
        }), 500


@search_bp.route('/suggestions')
def get_search_suggestions():
    """获取搜索建议"""
    try:
        query = request.args.get('q', '').strip()
        
        search_service = SearchService()
        suggestions = search_service._generate_suggestions(query)
        
        return jsonify({
            'success': True,
            'data': suggestions,
            'query': query,
            'message': '搜索建议获取成功'
        })
        
    except Exception as e:
        logger.error(f"Get suggestions error: {str(e)}")
        return jsonify({
            'success': False,
            'error': {
                'code': 'SUGGESTIONS_ERROR',
                'message': '获取搜索建议失败',
                'details': str(e)
            }
        }), 500


@search_bp.route('/popular')
def get_popular_searches():
    """获取热门搜索"""
    try:
        limit = min(request.args.get('limit', 10, type=int), 50)
        
        search_service = SearchService()
        popular_searches = search_service.get_popular_searches(limit)
        
        return jsonify({
            'success': True,
            'data': popular_searches,
            'limit': limit,
            'message': '热门搜索获取成功'
        })
        
    except Exception as e:
        logger.error(f"Get popular searches error: {str(e)}")
        return jsonify({
            'success': False,
            'error': {
                'code': 'POPULAR_SEARCHES_ERROR',
                'message': '获取热门搜索失败',
                'details': str(e)
            }
        }), 500


@search_bp.route('/stats')
def get_search_stats():
    """获取搜索统计信息"""
    try:
        search_service = SearchService()
        stats = search_service.get_search_statistics()
        
        return jsonify({
            'success': True,
            'data': stats,
            'message': '搜索统计获取成功'
        })
        
    except Exception as e:
        logger.error(f"Get search stats error: {str(e)}")
        return jsonify({
            'success': False,
            'error': {
                'code': 'SEARCH_STATS_ERROR',
                'message': '获取搜索统计失败',
                'details': str(e)
            }
        }), 500


@search_bp.route('/rebuild-index', methods=['POST'])
def rebuild_search_index():
    """重建搜索索引"""
    try:
        search_service = SearchService()
        result = search_service.rebuild_index()
        
        if result['success']:
            return jsonify({
                'success': True,
                'message': result['message']
            })
        else:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'REBUILD_INDEX_ERROR',
                    'message': '重建索引失败',
                    'details': result['error']
                }
            }), 500
            
    except Exception as e:
        logger.error(f"Rebuild index error: {str(e)}")
        return jsonify({
            'success': False,
            'error': {
                'code': 'REBUILD_INDEX_ERROR',
                'message': '重建索引失败',
                'details': str(e)
            }
        }), 500