"""
AI管理和监控路由
"""
from flask import Blueprint, jsonify, request
import logging
from app.services.ai_monitor import ai_monitor
from app.services.ai_config import ai_config_manager, AIModelConfig

logger = logging.getLogger(__name__)
ai_admin_bp = Blueprint('ai_admin', __name__)


@ai_admin_bp.route('/status')
def get_ai_status():
    """获取AI系统实时状态"""
    try:
        stats = ai_monitor.get_real_time_stats()
        
        return jsonify({
            'success': True,
            'data': stats,
            'message': 'AI状态获取成功'
        }), 200
        
    except Exception as e:
        logger.error(f"Get AI status error: {str(e)}")
        return jsonify({
            'success': False,
            'error': {
                'code': 'AI_STATUS_ERROR',
                'message': '获取AI状态失败',
                'details': str(e)
            }
        }), 500


@ai_admin_bp.route('/report/<period>')
def get_usage_report(period):
    """获取AI使用报告"""
    try:
        if period not in ['1h', '24h', '7d', '30d']:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'INVALID_PERIOD',
                    'message': '无效的时间周期',
                    'details': '支持的周期: 1h, 24h, 7d, 30d'
                }
            }), 400
        
        report = ai_monitor.generate_usage_report(period)
        
        # 将dataclass转换为字典
        from dataclasses import asdict
        report_data = asdict(report)
        
        return jsonify({
            'success': True,
            'data': report_data,
            'message': f'{period} AI使用报告生成成功'
        }), 200
        
    except Exception as e:
        logger.error(f"Get usage report error: {str(e)}")
        return jsonify({
            'success': False,
            'error': {
                'code': 'REPORT_ERROR',
                'message': '生成使用报告失败',
                'details': str(e)
            }
        }), 500


@ai_admin_bp.route('/config')
def get_ai_config():
    """获取AI配置信息"""
    try:
        providers = ai_config_manager.get_available_providers()
        primary_provider = ai_config_manager.get_primary_provider()
        
        config_info = {
            'providers': [],
            'primary_provider': primary_provider,
            'total_providers': len(providers)
        }
        
        for provider in providers:
            config = ai_config_manager.get_model_config(provider)
            stats = ai_config_manager.usage_stats.get(provider)
            
            provider_info = {
                'provider': provider,
                'model_name': config.model_name,
                'enabled': config.enabled,
                'max_tokens': config.max_tokens,
                'temperature': config.temperature,
                'daily_limit': config.daily_limit,
                'cost_per_1k_tokens': config.cost_per_1k_tokens,
                'usage_stats': {
                    'total_requests': stats.total_requests if stats else 0,
                    'daily_requests': stats.daily_requests if stats else 0,
                    'success_rate': (stats.successful_requests / max(stats.total_requests, 1)) * 100 if stats else 0,
                    'total_cost': stats.total_cost if stats else 0,
                    'daily_cost': stats.daily_cost if stats else 0
                }
            }
            config_info['providers'].append(provider_info)
        
        return jsonify({
            'success': True,
            'data': config_info,
            'message': 'AI配置信息获取成功'
        }), 200
        
    except Exception as e:
        logger.error(f"Get AI config error: {str(e)}")
        return jsonify({
            'success': False,
            'error': {
                'code': 'CONFIG_ERROR',
                'message': '获取AI配置失败',
                'details': str(e)
            }
        }), 500


@ai_admin_bp.route('/config', methods=['POST'])
def update_ai_config():
    """更新AI配置"""
    try:
        if not request.json:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'NO_DATA',
                    'message': '请提供配置数据'
                }
            }), 400
        
        provider = request.json.get('provider')
        if not provider:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'NO_PROVIDER',
                    'message': '请指定AI提供商'
                }
            }), 400
        
        # 更新配置
        updates = {}
        allowed_fields = ['enabled', 'max_tokens', 'temperature', 'daily_limit', 'cost_per_1k_tokens']
        
        for field in allowed_fields:
            if field in request.json:
                updates[field] = request.json[field]
        
        if updates:
            ai_config_manager.update_model_config(provider, **updates)
            
            return jsonify({
                'success': True,
                'data': {
                    'provider': provider,
                    'updated_fields': list(updates.keys())
                },
                'message': f'{provider} 配置更新成功'
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'NO_UPDATES',
                    'message': '没有提供有效的更新字段'
                }
            }), 400
            
    except Exception as e:
        logger.error(f"Update AI config error: {str(e)}")
        return jsonify({
            'success': False,
            'error': {
                'code': 'UPDATE_CONFIG_ERROR',
                'message': '更新AI配置失败',
                'details': str(e)
            }
        }), 500


@ai_admin_bp.route('/config/add', methods=['POST'])
def add_ai_provider():
    """添加新的AI提供商配置"""
    try:
        if not request.json:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'NO_DATA',
                    'message': '请提供配置数据'
                }
            }), 400
        
        # 必填字段验证
        required_fields = ['provider', 'model_name', 'api_key']
        for field in required_fields:
            if not request.json.get(field):
                return jsonify({
                    'success': False,
                    'error': {
                        'code': 'MISSING_FIELD',
                        'message': f'缺少必填字段: {field}'
                    }
                }), 400
        
        # 检查提供商是否已存在
        provider = request.json['provider']
        existing_config = ai_config_manager.get_model_config(provider)
        if existing_config:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'PROVIDER_EXISTS',
                    'message': f'提供商 {provider} 已存在，请使用更新接口'
                }
            }), 400
        
        # 创建新配置
        from app.services.ai_config import AIModelConfig
        new_config = AIModelConfig(
            provider=provider,
            model_name=request.json['model_name'],
            api_key=request.json['api_key'],
            api_base=request.json.get('api_base'),
            max_tokens=int(request.json.get('max_tokens', 2000)),
            temperature=float(request.json.get('temperature', 0.7)),
            timeout=int(request.json.get('timeout', 60)),
            enabled=bool(request.json.get('enabled', True)),
            cost_per_1k_tokens=float(request.json.get('cost_per_1k_tokens', 0.0)),
            daily_limit=int(request.json.get('daily_limit', 10000))
        )
        
        # 添加配置
        ai_config_manager.add_model_config(new_config)
        
        return jsonify({
            'success': True,
            'data': {
                'provider': provider,
                'model_name': new_config.model_name,
                'enabled': new_config.enabled
            },
            'message': f'AI提供商 {provider} 添加成功'
        }), 201
        
    except Exception as e:
        logger.error(f"Add AI provider error: {str(e)}")
        return jsonify({
            'success': False,
            'error': {
                'code': 'ADD_PROVIDER_ERROR',
                'message': '添加AI提供商失败',
                'details': str(e)
            }
        }), 500


@ai_admin_bp.route('/config/<provider>', methods=['DELETE'])
def remove_ai_provider(provider):
    """删除AI提供商配置"""
    try:
        existing_config = ai_config_manager.get_model_config(provider)
        if not existing_config:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'PROVIDER_NOT_FOUND',
                    'message': f'提供商 {provider} 不存在'
                }
            }), 404
        
        # 删除配置
        ai_config_manager.remove_model_config(provider)
        
        return jsonify({
            'success': True,
            'data': {
                'provider': provider
            },
            'message': f'AI提供商 {provider} 删除成功'
        }), 200
        
    except Exception as e:
        logger.error(f"Remove AI provider error: {str(e)}")
        return jsonify({
            'success': False,
            'error': {
                'code': 'REMOVE_PROVIDER_ERROR',
                'message': '删除AI提供商失败',
                'details': str(e)
            }
        }), 500


@ai_admin_bp.route('/config/test/<provider>')
def test_provider_connection(provider):
    """测试AI提供商连接"""
    try:
        result = ai_config_manager.test_provider_connection(provider)
        
        if result['success']:
            return jsonify({
                'success': True,
                'data': result,
                'message': f'{provider} 连接测试成功'
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'CONNECTION_FAILED',
                    'message': f'{provider} 连接测试失败',
                    'details': result.get('error', '未知错误')
                }
            }), 400
            
    except Exception as e:
        logger.error(f"Test provider connection error: {str(e)}")
        return jsonify({
            'success': False,
            'error': {
                'code': 'TEST_ERROR',
                'message': '连接测试失败',
                'details': str(e)
            }
        }), 500


@ai_admin_bp.route('/stats/reset', methods=['POST'])
def reset_daily_stats():
    """重置每日统计"""
    try:
        ai_config_manager.reset_daily_stats()
        
        return jsonify({
            'success': True,
            'data': {
                'reset_time': ai_config_manager.usage_stats
            },
            'message': '每日统计重置成功'
        }), 200
        
    except Exception as e:
        logger.error(f"Reset daily stats error: {str(e)}")
        return jsonify({
            'success': False,
            'error': {
                'code': 'RESET_ERROR',
                'message': '重置统计失败',
                'details': str(e)
            }
        }), 500


@ai_admin_bp.route('/report/<period>/export')
def export_usage_report(period):
    """导出AI使用报告"""
    try:
        if period not in ['1h', '24h', '7d', '30d']:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'INVALID_PERIOD',
                    'message': '无效的时间周期'
                }
            }), 400
        
        report = ai_monitor.generate_usage_report(period)
        export_format = request.args.get('format', 'json')
        
        if export_format.lower() not in ['json']:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'INVALID_FORMAT',
                    'message': '暂只支持JSON格式导出'
                }
            }), 400
        
        exported_data = ai_monitor.export_report(report, export_format)
        
        return jsonify({
            'success': True,
            'data': {
                'period': period,
                'format': export_format,
                'content': exported_data
            },
            'message': '报告导出成功'
        }), 200
        
    except Exception as e:
        logger.error(f"Export usage report error: {str(e)}")
        return jsonify({
            'success': False,
            'error': {
                'code': 'EXPORT_ERROR',
                'message': '导出报告失败',
                'details': str(e)
            }
        }), 500


@ai_admin_bp.route('/providers')
def list_providers():
    """列出所有支持的AI提供商"""
    try:
        from app.services.ai_config import AIProvider
        
        all_providers = {}
        for provider in AIProvider:
            config = ai_config_manager.get_model_config(provider.value)
            all_providers[provider.value] = {
                'name': provider.value,
                'configured': config is not None,
                'enabled': config.enabled if config else False,
                'model': config.model_name if config else None,
                'description': f'{provider.value.title()} AI Provider'
            }
        
        return jsonify({
            'success': True,
            'data': {
                'providers': all_providers,
                'total_supported': len(all_providers),
                'total_configured': len([p for p in all_providers.values() if p['configured']])
            },
            'message': '提供商列表获取成功'
        }), 200
        
    except Exception as e:
        logger.error(f"List providers error: {str(e)}")
        return jsonify({
            'success': False,
            'error': {
                'code': 'PROVIDERS_ERROR',
                'message': '获取提供商列表失败',
                'details': str(e)
            }
        }), 500


@ai_admin_bp.route('/health')
def get_system_health():
    """获取AI系统健康状态"""
    try:
        stats = ai_monitor.get_real_time_stats()
        health_info = stats.get('system_health', {})
        
        return jsonify({
            'success': True,
            'data': health_info,
            'message': '系统健康状态获取成功'
        }), 200
        
    except Exception as e:
        logger.error(f"Get system health error: {str(e)}")
        return jsonify({
            'success': False,
            'error': {
                'code': 'HEALTH_ERROR',
                'message': '获取系统健康状态失败',
                'details': str(e)
            }
        }), 500


@ai_admin_bp.route('/optimize', methods=['POST'])
def optimize_ai_usage():
    """AI使用优化建议"""
    try:
        # 生成最近24小时的报告
        report = ai_monitor.generate_usage_report('24h')
        
        # 获取优化建议
        optimization_tips = {
            'performance': [],
            'cost': [],
            'quality': []
        }
        
        # 性能优化建议
        if report.extraction_metrics.success_rate < 0.8:
            optimization_tips['performance'].append('考虑切换到更稳定的AI提供商')
        
        if report.extraction_metrics.avg_processing_time > 30:
            optimization_tips['performance'].append('处理时间较长，建议优化提示词长度')
        
        # 成本优化建议
        total_cost = report.cost_analysis.get('daily_cost', 0)
        if total_cost > 10:  # 假设每日成本阈值
            optimization_tips['cost'].append('每日成本较高，建议优化使用频率或选择更经济的模型')
        
        # 质量优化建议
        if report.extraction_metrics.avg_confidence < 0.7:
            optimization_tips['quality'].append('提取质量有待提升，建议优化提示词或增加样本训练')
        
        if report.classification_metrics.avg_confidence < 0.8:
            optimization_tips['quality'].append('分类准确度需要改进，考虑增加分类规则或样本')
        
        return jsonify({
            'success': True,
            'data': {
                'optimization_tips': optimization_tips,
                'report_summary': {
                    'extraction_success_rate': report.extraction_metrics.success_rate,
                    'classification_confidence': report.classification_metrics.avg_confidence,
                    'daily_cost': report.cost_analysis.get('daily_cost', 0),
                    'recommendations': report.recommendations
                }
            },
            'message': 'AI使用优化建议生成成功'
        }), 200
        
    except Exception as e:
        logger.error(f"Optimize AI usage error: {str(e)}")
        return jsonify({
            'success': False,
            'error': {
                'code': 'OPTIMIZE_ERROR',
                'message': '生成优化建议失败',
                'details': str(e)
            }
        }), 500