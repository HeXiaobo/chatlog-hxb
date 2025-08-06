"""
问答分类服务
"""
import re
import logging
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class CategoryMatch:
    """分类匹配结果"""
    category_id: int
    category_name: str
    confidence: float
    matched_keywords: List[str]


class QAClassifier:
    """问答智能分类器"""
    
    def __init__(self):
        self.category_rules = self._init_category_rules()
        self.default_category_id = 1  # 默认为"产品咨询"
        self.confidence_threshold = 0.3
    
    def _init_category_rules(self) -> Dict[int, Dict[str, any]]:
        """初始化分类规则"""
        return {
            1: {  # 产品咨询
                'name': '产品咨询',
                'keywords': [
                    '功能', '特性', '产品', '版本', '支持', '兼容', '区别',
                    '对比', '选择', '推荐', '介绍', '什么是', '有什么',
                    '能做', '可以', '支持哪些', '包含', '提供'
                ],
                'patterns': [
                    r'(产品|软件|工具|系统).*(功能|特性|介绍)',
                    r'(什么是|介绍.*)(产品|功能|特性)',
                    r'(支持|兼容|包含).*(格式|平台|系统)',
                    r'(推荐|建议|选择).*(产品|方案|工具)',
                    r'.*有什么.*(功能|特点|优势)',
                ],
                'weight': 1.0
            },
            2: {  # 技术支持
                'name': '技术支持',
                'keywords': [
                    '报错', '错误', '异常', '故障', '问题', '不能', '无法',
                    '失败', '崩溃', '卡住', 'bug', '修复', '解决', '处理',
                    '调试', '排查', '检查', '诊断', '日志', '代码'
                ],
                'patterns': [
                    r'.*(报错|错误|异常|故障|问题).*',
                    r'.*(不能|无法|失败|崩溃).*',
                    r'.*(修复|解决|处理|调试).*',
                    r'.*为什么.*(不能|无法|失败)',
                    r'.*(检查|诊断|排查).*(问题|错误)',
                    r'.*(代码|程序|脚本).*(错误|问题)',
                ],
                'weight': 1.2  # 技术问题权重稍高
            },
            3: {  # 价格费用
                'name': '价格费用',
                'keywords': [
                    '价格', '费用', '收费', '付费', '免费', '成本', '多少钱',
                    '报价', '优惠', '折扣', '套餐', '版本', '授权', '许可',
                    '订阅', '购买', '试用', '升级', '续费'
                ],
                'patterns': [
                    r'.*(价格|费用|收费|多少钱|报价).*',
                    r'.*(免费|付费|订阅|购买).*',
                    r'.*(优惠|折扣|套餐|版本).*',
                    r'.*(试用|升级|续费|授权).*',
                ],
                'weight': 1.1
            },
            4: {  # 使用教程
                'name': '使用教程',
                'keywords': [
                    '如何', '怎么', '怎样', '教程', '指南', '说明', '步骤',
                    '操作', '使用', '设置', '配置', '安装', '部署', '运行',
                    '启动', '开始', '入门', '学习', '文档', '手册'
                ],
                'patterns': [
                    r'^(如何|怎么|怎样).*',
                    r'.*(教程|指南|说明|步骤|操作).*',
                    r'.*(设置|配置|安装|部署).*',
                    r'.*(使用|学习|入门).*方法',
                    r'.*教我.*(使用|操作|设置)',
                    r'.*(第一步|首先|然后|接下来).*',
                ],
                'weight': 1.0
            },
            5: {  # 售后问题
                'name': '售后问题',
                'keywords': [
                    '售后', '客服', '支持', '服务', '反馈', '建议', '投诉',
                    '退款', '退货', '换货', '保修', '维护', '联系', '咨询',
                    '申请', '工单', '回复', '处理', '跟进'
                ],
                'patterns': [
                    r'.*(售后|客服|服务|支持).*',
                    r'.*(反馈|建议|投诉|申请).*',
                    r'.*(退款|退货|换货|保修).*',
                    r'.*(联系|咨询|工单).*',
                    r'.*如何.*联系',
                ],
                'weight': 0.9
            }
        }
    
    def classify_qa(self, question: str, answer: str, context: List[str] = None) -> CategoryMatch:
        """
        对问答对进行分类
        
        Args:
            question: 问题内容
            answer: 答案内容
            context: 上下文信息
        
        Returns:
            CategoryMatch: 分类结果
        """
        # 组合文本进行分析
        combined_text = question
        if answer:
            combined_text += " " + answer
        if context:
            combined_text += " " + " ".join(context)
        
        # 计算每个分类的得分
        category_scores = {}
        
        for category_id, rule in self.category_rules.items():
            score = self._calculate_category_score(combined_text, rule)
            if score > 0:
                category_scores[category_id] = score
        
        # 选择得分最高的分类
        if category_scores:
            best_category_id = max(category_scores.items(), key=lambda x: x[1])[0]
            best_score = category_scores[best_category_id]
            
            if best_score >= self.confidence_threshold:
                matched_keywords = self._get_matched_keywords(
                    combined_text, 
                    self.category_rules[best_category_id]
                )
                
                return CategoryMatch(
                    category_id=best_category_id,
                    category_name=self.category_rules[best_category_id]['name'],
                    confidence=min(best_score, 1.0),
                    matched_keywords=matched_keywords
                )
        
        # 使用默认分类
        return CategoryMatch(
            category_id=self.default_category_id,
            category_name=self.category_rules[self.default_category_id]['name'],
            confidence=0.2,
            matched_keywords=[]
        )
    
    def _calculate_category_score(self, text: str, rule: Dict[str, any]) -> float:
        """计算分类得分"""
        score = 0.0
        text_lower = text.lower()
        
        # 关键词匹配
        keyword_matches = 0
        for keyword in rule['keywords']:
            if keyword in text_lower:
                keyword_matches += 1
        
        if keyword_matches > 0:
            keyword_score = (keyword_matches / len(rule['keywords'])) * 0.6
            score += keyword_score
        
        # 模式匹配
        pattern_matches = 0
        for pattern in rule['patterns']:
            if re.search(pattern, text, re.IGNORECASE):
                pattern_matches += 1
        
        if pattern_matches > 0:
            pattern_score = (pattern_matches / len(rule['patterns'])) * 0.4
            score += pattern_score
        
        # 应用权重
        score *= rule.get('weight', 1.0)
        
        # 文本长度调整
        if len(text) > 100:
            score *= 1.1  # 长文本稍微加权
        
        return score
    
    def _get_matched_keywords(self, text: str, rule: Dict[str, any]) -> List[str]:
        """获取匹配的关键词"""
        matched = []
        text_lower = text.lower()
        
        for keyword in rule['keywords']:
            if keyword in text_lower:
                matched.append(keyword)
        
        return matched
    
    def batch_classify(self, qa_pairs: List[Tuple[str, str, List[str]]]) -> List[CategoryMatch]:
        """
        批量分类问答对
        
        Args:
            qa_pairs: [(question, answer, context)] 列表
        
        Returns:
            List[CategoryMatch]: 分类结果列表
        """
        results = []
        
        for question, answer, context in qa_pairs:
            try:
                result = self.classify_qa(question, answer, context)
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to classify QA: {str(e)}")
                # 使用默认分类
                results.append(CategoryMatch(
                    category_id=self.default_category_id,
                    category_name=self.category_rules[self.default_category_id]['name'],
                    confidence=0.1,
                    matched_keywords=[]
                ))
        
        return results
    
    def get_classification_stats(self, results: List[CategoryMatch]) -> Dict[str, any]:
        """获取分类统计信息"""
        if not results:
            return {
                'total_classified': 0,
                'avg_confidence': 0,
                'category_distribution': {},
                'classification_quality': 'poor'
            }
        
        # 分类分布
        category_dist = {}
        confidences = []
        
        for result in results:
            category_name = result.category_name
            category_dist[category_name] = category_dist.get(category_name, 0) + 1
            confidences.append(result.confidence)
        
        avg_confidence = sum(confidences) / len(confidences)
        
        # 分类质量评估
        quality = 'excellent' if avg_confidence >= 0.8 else \
                  'good' if avg_confidence >= 0.6 else \
                  'fair' if avg_confidence >= 0.4 else 'poor'
        
        return {
            'total_classified': len(results),
            'avg_confidence': round(avg_confidence, 3),
            'category_distribution': category_dist,
            'classification_quality': quality,
            'high_confidence_ratio': len([c for c in confidences if c >= 0.6]) / len(confidences)
        }
    
    def add_custom_rule(self, category_id: int, name: str, keywords: List[str], 
                       patterns: List[str] = None, weight: float = 1.0):
        """添加自定义分类规则"""
        self.category_rules[category_id] = {
            'name': name,
            'keywords': keywords,
            'patterns': patterns or [],
            'weight': weight
        }
    
    def update_category_rule(self, category_id: int, **kwargs):
        """更新分类规则"""
        if category_id in self.category_rules:
            self.category_rules[category_id].update(kwargs)
    
    def get_category_suggestions(self, text: str, top_k: int = 3) -> List[Tuple[int, str, float]]:
        """获取分类建议"""
        scores = []
        
        for category_id, rule in self.category_rules.items():
            score = self._calculate_category_score(text, rule)
            if score > 0:
                scores.append((category_id, rule['name'], score))
        
        # 按得分排序并返回前K个
        scores.sort(key=lambda x: x[2], reverse=True)
        return scores[:top_k]