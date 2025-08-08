"""
AI处理监控和统计服务
"""
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from collections import defaultdict

from sqlalchemy import func, and_, or_
from app import db
from app.models import QAPair, UploadHistory
from .ai_config import ai_config_manager

logger = logging.getLogger(__name__)


@dataclass
class AIPerformanceMetrics:
    """AI性能指标"""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    avg_processing_time: float = 0.0
    total_tokens_used: int = 0
    total_cost: float = 0.0
    success_rate: float = 0.0
    avg_confidence: float = 0.0
    quality_distribution: Dict[str, int] = None
    
    def __post_init__(self):
        if self.quality_distribution is None:
            self.quality_distribution = {}


@dataclass
class AIUsageReport:
    """AI使用报告"""
    period: str
    start_date: str
    end_date: str
    extraction_metrics: AIPerformanceMetrics
    classification_metrics: AIPerformanceMetrics
    provider_breakdown: Dict[str, AIPerformanceMetrics]
    cost_analysis: Dict[str, float]
    recommendations: List[str]


class AIMonitor:
    """AI处理监控器"""
    
    def __init__(self):
        self.performance_cache = {}
        self.cache_expiry = 300  # 5分钟缓存
        self.session_records = []  # 临时存储会话记录用于测试
        
    def get_real_time_stats(self) -> Dict[str, Any]:
        """获取实时统计信息"""
        try:
            # 获取AI配置状态
            config_status = self._get_config_status()
            
            # 获取当前处理状态
            processing_status = self._get_processing_status()
            
            # 获取使用统计
            usage_stats = ai_config_manager.get_usage_summary()
            
            # 获取质量指标
            quality_metrics = self._get_quality_metrics()
            
            return {
                'timestamp': datetime.now().isoformat(),
                'config_status': config_status,
                'processing_status': processing_status,
                'usage_stats': usage_stats,
                'quality_metrics': quality_metrics,
                'system_health': self._assess_system_health(config_status, usage_stats)
            }
            
        except Exception as e:
            logger.error(f"Failed to get real-time stats: {str(e)}")
            return {'error': str(e)}
    
    def _get_config_status(self) -> Dict[str, Any]:
        """获取AI配置状态"""
        providers = ai_config_manager.get_available_providers()
        primary_provider = ai_config_manager.get_primary_provider()
        
        provider_status = {}
        for provider in providers:
            config = ai_config_manager.get_model_config(provider)
            stats = ai_config_manager.usage_stats.get(provider)
            
            provider_status[provider] = {
                'enabled': config.enabled,
                'model': config.model_name,
                'daily_limit': config.daily_limit,
                'daily_used': stats.daily_requests if stats else 0,
                'remaining': max(0, config.daily_limit - (stats.daily_requests if stats else 0)),
                'cost_per_1k': config.cost_per_1k_tokens,
                'can_make_request': ai_config_manager.can_make_request(provider)
            }
        
        return {
            'total_providers': len(providers),
            'primary_provider': primary_provider,
            'providers': provider_status,
            'ai_enabled': len(providers) > 0
        }
    
    def _get_processing_status(self) -> Dict[str, Any]:
        """获取当前处理状态"""
        try:
            # 查询最近的处理记录
            recent_uploads = UploadHistory.query.filter(
                UploadHistory.uploaded_at >= datetime.utcnow() - timedelta(hours=24)
            ).order_by(UploadHistory.uploaded_at.desc()).limit(100).all()
            
            # 统计处理状态
            status_counts = defaultdict(int)
            ai_processed = 0
            total_processing_time = 0
            
            for upload in recent_uploads:
                status_counts[upload.status] += 1
                if upload.processing_time:
                    total_processing_time += upload.processing_time
                
                # 检查是否是AI处理
                if upload.source_file and '_ai' in upload.source_file:
                    ai_processed += 1
            
            avg_processing_time = total_processing_time / len(recent_uploads) if recent_uploads else 0
            
            return {
                'recent_uploads_24h': len(recent_uploads),
                'ai_processed_count': ai_processed,
                'ai_processing_ratio': ai_processed / len(recent_uploads) if recent_uploads else 0,
                'status_distribution': dict(status_counts),
                'avg_processing_time': round(avg_processing_time, 2)
            }
            
        except Exception as e:
            logger.error(f"Failed to get processing status: {str(e)}")
            return {'error': str(e)}
    
    def _get_quality_metrics(self) -> Dict[str, Any]:
        """获取质量指标"""
        try:
            # 查询AI处理的问答对
            ai_qa_pairs = QAPair.query.filter(
                or_(
                    QAPair.source_file.like('%_ai'),
                    QAPair.original_context.like('%ai_processed%')
                )
            ).all()
            
            if not ai_qa_pairs:
                return {
                    'total_ai_qa_pairs': 0,
                    'avg_confidence': 0,
                    'quality_distribution': {},
                    'high_quality_ratio': 0
                }
            
            # 计算质量指标
            confidences = [qa.confidence for qa in ai_qa_pairs]
            avg_confidence = sum(confidences) / len(confidences)
            
            # 质量分布
            quality_dist = {
                'excellent': len([c for c in confidences if c >= 0.9]),
                'good': len([c for c in confidences if 0.7 <= c < 0.9]),
                'fair': len([c for c in confidences if 0.5 <= c < 0.7]),
                'poor': len([c for c in confidences if c < 0.5])
            }
            
            high_quality_count = quality_dist['excellent'] + quality_dist['good']
            high_quality_ratio = high_quality_count / len(ai_qa_pairs)
            
            return {
                'total_ai_qa_pairs': len(ai_qa_pairs),
                'avg_confidence': round(avg_confidence, 3),
                'quality_distribution': quality_dist,
                'high_quality_ratio': round(high_quality_ratio, 3)
            }
            
        except Exception as e:
            logger.error(f"Failed to get quality metrics: {str(e)}")
            return {'error': str(e)}
    
    def _assess_system_health(self, config_status: Dict, usage_stats: Dict) -> Dict[str, Any]:
        """评估系统健康状态"""
        try:
            health_score = 100
            issues = []
            recommendations = []
            
            # 检查AI配置
            if not config_status.get('ai_enabled', False):
                health_score -= 30
                issues.append('AI功能未配置')
                recommendations.append('配置至少一个AI提供商')
            
            # 检查使用限制
            for provider, status in config_status.get('providers', {}).items():
                remaining_ratio = status['remaining'] / status['daily_limit']
                if remaining_ratio < 0.1:  # 剩余不足10%
                    health_score -= 20
                    issues.append(f'{provider} 接近每日限制')
                    recommendations.append(f'考虑增加 {provider} 的每日限制')
                elif remaining_ratio < 0.3:  # 剩余不足30%
                    health_score -= 10
                    issues.append(f'{provider} 使用量较高')
            
            # 检查成功率
            total_requests = usage_stats.get('total_requests', 0)
            if total_requests > 0:
                for provider, stats in usage_stats.get('providers', {}).items():
                    success_rate = stats.get('success_rate', 100)
                    if success_rate < 80:
                        health_score -= 25
                        issues.append(f'{provider} 成功率低于80%')
                        recommendations.append(f'检查 {provider} 的配置和网络连接')
                    elif success_rate < 95:
                        health_score -= 10
                        issues.append(f'{provider} 成功率低于95%')
            
            # 评估健康等级
            if health_score >= 90:
                health_level = 'excellent'
            elif health_score >= 70:
                health_level = 'good'
            elif health_score >= 50:
                health_level = 'fair'
            else:
                health_level = 'poor'
            
            return {
                'health_score': health_score,
                'health_level': health_level,
                'issues': issues,
                'recommendations': recommendations
            }
            
        except Exception as e:
            logger.error(f"Failed to assess system health: {str(e)}")
            return {'error': str(e)}
    
    def generate_usage_report(self, period: str = '24h') -> AIUsageReport:
        """生成AI使用报告"""
        try:
            # 计算时间范围
            end_date = datetime.utcnow()
            if period == '1h':
                start_date = end_date - timedelta(hours=1)
            elif period == '24h':
                start_date = end_date - timedelta(days=1)
            elif period == '7d':
                start_date = end_date - timedelta(days=7)
            elif period == '30d':
                start_date = end_date - timedelta(days=30)
            else:
                start_date = end_date - timedelta(days=1)
            
            # 获取期间内的数据
            period_uploads = UploadHistory.query.filter(
                and_(
                    UploadHistory.uploaded_at >= start_date,
                    UploadHistory.uploaded_at <= end_date
                )
            ).all()
            
            period_qa_pairs = QAPair.query.filter(
                and_(
                    QAPair.created_at >= start_date,
                    QAPair.created_at <= end_date
                )
            ).all()
            
            # 分析提取性能
            extraction_metrics = self._analyze_extraction_performance(period_uploads, period_qa_pairs)
            
            # 分析分类性能
            classification_metrics = self._analyze_classification_performance(period_qa_pairs)
            
            # 提供商分析
            provider_breakdown = self._analyze_provider_performance(period_uploads, period_qa_pairs)
            
            # 成本分析
            cost_analysis = self._analyze_costs(period_uploads, period_qa_pairs)
            
            # 生成建议
            recommendations = self._generate_recommendations(extraction_metrics, classification_metrics, provider_breakdown)
            
            return AIUsageReport(
                period=period,
                start_date=start_date.isoformat(),
                end_date=end_date.isoformat(),
                extraction_metrics=extraction_metrics,
                classification_metrics=classification_metrics,
                provider_breakdown=provider_breakdown,
                cost_analysis=cost_analysis,
                recommendations=recommendations
            )
            
        except Exception as e:
            logger.error(f"Failed to generate usage report: {str(e)}")
            return AIUsageReport(
                period=period,
                start_date='',
                end_date='',
                extraction_metrics=AIPerformanceMetrics(),
                classification_metrics=AIPerformanceMetrics(),
                provider_breakdown={},
                cost_analysis={},
                recommendations=[f'报告生成失败: {str(e)}']
            )
    
    def _analyze_extraction_performance(self, uploads: List, qa_pairs: List) -> AIPerformanceMetrics:
        """分析提取性能"""
        try:
            ai_uploads = [u for u in uploads if u.source_file and '_ai' in str(u.source_file)]
            ai_qa_pairs = [qa for qa in qa_pairs if qa.source_file and '_ai' in qa.source_file]
            
            if not ai_uploads:
                return AIPerformanceMetrics()
            
            total_requests = len(ai_uploads)
            successful_requests = len([u for u in ai_uploads if u.status == 'completed'])
            failed_requests = total_requests - successful_requests
            
            processing_times = [u.processing_time for u in ai_uploads if u.processing_time]
            avg_processing_time = sum(processing_times) / len(processing_times) if processing_times else 0
            
            confidences = [qa.confidence for qa in ai_qa_pairs]
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0
            
            # 质量分布
            quality_dist = {
                'high': len([c for c in confidences if c >= 0.8]),
                'medium': len([c for c in confidences if 0.6 <= c < 0.8]),
                'low': len([c for c in confidences if c < 0.6])
            }
            
            return AIPerformanceMetrics(
                total_requests=total_requests,
                successful_requests=successful_requests,
                failed_requests=failed_requests,
                avg_processing_time=round(avg_processing_time, 2),
                success_rate=successful_requests / total_requests if total_requests > 0 else 0,
                avg_confidence=round(avg_confidence, 3),
                quality_distribution=quality_dist
            )
            
        except Exception as e:
            logger.error(f"Failed to analyze extraction performance: {str(e)}")
            return AIPerformanceMetrics()
    
    def _analyze_classification_performance(self, qa_pairs: List) -> AIPerformanceMetrics:
        """分析分类性能"""
        try:
            ai_classified = []
            for qa in qa_pairs:
                try:
                    if qa.original_context:
                        context = json.loads(qa.original_context)
                        if context.get('ai_processed') or context.get('classification_method') == 'ai':
                            ai_classified.append(qa)
                except:
                    continue
            
            if not ai_classified:
                return AIPerformanceMetrics()
            
            # 分类置信度分析
            classification_confidences = []
            for qa in ai_classified:
                try:
                    context = json.loads(qa.original_context)
                    conf = context.get('classification_confidence', qa.confidence)
                    classification_confidences.append(conf)
                except:
                    classification_confidences.append(qa.confidence)
            
            avg_confidence = sum(classification_confidences) / len(classification_confidences)
            
            # 质量分布
            quality_dist = {
                'high': len([c for c in classification_confidences if c >= 0.8]),
                'medium': len([c for c in classification_confidences if 0.6 <= c < 0.8]),
                'low': len([c for c in classification_confidences if c < 0.6])
            }
            
            return AIPerformanceMetrics(
                total_requests=len(ai_classified),
                successful_requests=len(ai_classified),
                failed_requests=0,
                success_rate=1.0,
                avg_confidence=round(avg_confidence, 3),
                quality_distribution=quality_dist
            )
            
        except Exception as e:
            logger.error(f"Failed to analyze classification performance: {str(e)}")
            return AIPerformanceMetrics()
    
    def _analyze_provider_performance(self, uploads: List, qa_pairs: List) -> Dict[str, AIPerformanceMetrics]:
        """分析提供商性能"""
        provider_stats = {}
        
        try:
            # 从AI配置获取使用统计
            for provider, stats in ai_config_manager.usage_stats.items():
                provider_stats[provider] = AIPerformanceMetrics(
                    total_requests=stats.total_requests,
                    successful_requests=stats.successful_requests,
                    failed_requests=stats.failed_requests,
                    total_tokens_used=stats.total_tokens_used,
                    total_cost=stats.total_cost,
                    success_rate=stats.successful_requests / max(stats.total_requests, 1)
                )
            
        except Exception as e:
            logger.error(f"Failed to analyze provider performance: {str(e)}")
        
        return provider_stats
    
    def _analyze_costs(self, uploads: List, qa_pairs: List) -> Dict[str, float]:
        """分析成本"""
        try:
            usage_summary = ai_config_manager.get_usage_summary()
            
            cost_breakdown = {
                'total_cost': usage_summary.get('total_cost', 0),
                'daily_cost': 0,
                'estimated_monthly_cost': 0
            }
            
            # 计算每日成本
            daily_costs = []
            for provider, stats in usage_summary.get('providers', {}).items():
                daily_cost = stats.get('daily_usage', {}).get('cost', 0)
                daily_costs.append(daily_cost)
            
            cost_breakdown['daily_cost'] = sum(daily_costs)
            cost_breakdown['estimated_monthly_cost'] = cost_breakdown['daily_cost'] * 30
            
            return cost_breakdown
            
        except Exception as e:
            logger.error(f"Failed to analyze costs: {str(e)}")
            return {'error': str(e)}
    
    def _generate_recommendations(self, extraction_metrics: AIPerformanceMetrics,
                                classification_metrics: AIPerformanceMetrics,
                                provider_breakdown: Dict) -> List[str]:
        """生成优化建议"""
        recommendations = []
        
        try:
            # 提取性能建议
            if extraction_metrics.success_rate < 0.8:
                recommendations.append('提取成功率较低，建议检查AI提示词设置和数据质量')
            
            if extraction_metrics.avg_confidence < 0.6:
                recommendations.append('提取置信度偏低，考虑优化提示词或使用更强的模型')
            
            # 分类性能建议
            if classification_metrics.avg_confidence < 0.7:
                recommendations.append('分类置信度有待提升，建议增加分类样本或优化分类规则')
            
            # 提供商建议
            best_provider = None
            best_success_rate = 0
            for provider, metrics in provider_breakdown.items():
                if metrics.success_rate > best_success_rate:
                    best_success_rate = metrics.success_rate
                    best_provider = provider
            
            if best_provider and best_success_rate > 0.9:
                recommendations.append(f'建议优先使用 {best_provider}，其成功率最高')
            
            # 成本优化建议
            if len(provider_breakdown) > 1:
                recommendations.append('考虑基于成本和性能选择最优的AI提供商组合')
            
            if not recommendations:
                recommendations.append('系统运行良好，继续保持当前配置')
            
        except Exception as e:
            logger.error(f"Failed to generate recommendations: {str(e)}")
            recommendations.append('建议生成失败，请检查系统状态')
        
        return recommendations
    
    def export_report(self, report: AIUsageReport, format: str = 'json') -> str:
        """导出报告"""
        try:
            if format.lower() == 'json':
                return json.dumps(asdict(report), indent=2, ensure_ascii=False)
            else:
                raise ValueError(f"不支持的格式: {format}")
                
        except Exception as e:
            logger.error(f"Failed to export report: {str(e)}")
            return f"导出失败: {str(e)}"
    
    def record_processing_session(self, provider: str, tokens_used: int, processing_time: float, 
                                 success: bool, quality_score: float = 0.0):
        """记录处理会话 (用于测试)"""
        session_record = {
            'timestamp': datetime.now().isoformat(),
            'provider': provider,
            'tokens_used': tokens_used,
            'processing_time': processing_time,
            'success': success,
            'quality_score': quality_score
        }
        self.session_records.append(session_record)
        logger.info(f"Recorded processing session: {provider}, success: {success}, tokens: {tokens_used}")
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """获取处理统计信息 (用于测试)"""
        if not self.session_records:
            return {
                'total_sessions': 0,
                'success_rate': 0.0,
                'total_tokens': 0,
                'avg_processing_time': 0.0
            }
        
        total_sessions = len(self.session_records)
        successful_sessions = sum(1 for record in self.session_records if record['success'])
        success_rate = successful_sessions / total_sessions if total_sessions > 0 else 0.0
        total_tokens = sum(record['tokens_used'] for record in self.session_records)
        total_time = sum(record['processing_time'] for record in self.session_records)
        avg_processing_time = total_time / total_sessions if total_sessions > 0 else 0.0
        
        return {
            'total_sessions': total_sessions,
            'success_rate': success_rate,
            'total_tokens': total_tokens,
            'avg_processing_time': avg_processing_time
        }
    
    def get_detailed_report(self, period_hours: int = 24) -> Dict[str, Any]:
        """获取详细报告 (用于测试)"""
        stats = self.get_processing_stats()
        
        # 提供商分析
        provider_stats = {}
        for record in self.session_records:
            provider = record['provider']
            if provider not in provider_stats:
                provider_stats[provider] = {
                    'sessions': 0,
                    'successful_sessions': 0,
                    'tokens_used': 0,
                    'processing_time': 0.0
                }
            
            provider_stats[provider]['sessions'] += 1
            if record['success']:
                provider_stats[provider]['successful_sessions'] += 1
            provider_stats[provider]['tokens_used'] += record['tokens_used']
            provider_stats[provider]['processing_time'] += record['processing_time']
        
        return {
            'summary': stats,
            'providers': provider_stats,
            'period_hours': period_hours,
            'report_generated_at': datetime.now().isoformat()
        }


# 全局监控实例
ai_monitor = AIMonitor()