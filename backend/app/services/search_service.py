"""
搜索服务 - 支持FTS5全文搜索
"""
import re
import jieba
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from sqlalchemy import text, func
from app import db
from app.models import QAPair, Category
from app.utils.cache import search_cache, category_cache

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """搜索结果"""
    qa_pairs: List[QAPair]
    total_count: int
    page: int
    per_page: int
    pages: int
    query: str
    search_time: float
    suggestions: List[str] = None


class SearchService:
    """搜索服务"""
    
    def __init__(self):
        self.fts_enabled = False
        self._init_fts()
        
        # 停用词列表
        self.stop_words = {'的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都', '一', '一个', '上', '也', '很', '到', '说', '要', '去', '你', '会', '着', '没有', '看', '好', '自己', '这'}
        
        # 同义词映射
        self.synonyms = {
            '如何': ['怎么', '怎样', '方法'],
            '什么': ['啥', '什么东西'],
            '为什么': ['为何', '怎么回事'],
            '价格': ['费用', '多少钱', '成本'],
            '问题': ['故障', '错误', '异常']
        }
    
    def _init_fts(self):
        """初始化FTS5全文搜索"""
        try:
            # 检查是否已有FTS表
            result = db.session.execute(text(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='qa_pairs_fts'"
            )).fetchone()
            
            if not result:
                # 创建FTS5虚拟表
                db.session.execute(text("""
                    CREATE VIRTUAL TABLE qa_pairs_fts USING fts5(
                        question, 
                        answer, 
                        category_name,
                        advisor,
                        content='qa_pairs',
                        content_rowid='id',
                        tokenize='unicode61'
                    )
                """))
                
                # 插入现有数据
                self._rebuild_fts_index()
                
                logger.info("FTS5 virtual table created successfully")
            
            self.fts_enabled = True
            
        except Exception as e:
            logger.warning(f"Failed to initialize FTS5: {str(e)}, falling back to LIKE search")
            self.fts_enabled = False
    
    def _rebuild_fts_index(self):
        """重建FTS索引"""
        try:
            if not self.fts_enabled:
                return
            
            # 清空FTS表
            db.session.execute(text("DELETE FROM qa_pairs_fts"))
            
            # 重新插入所有数据
            db.session.execute(text("""
                INSERT INTO qa_pairs_fts(rowid, question, answer, category_name, advisor)
                SELECT qa.id, qa.question, qa.answer, 
                       COALESCE(c.name, ''), COALESCE(qa.advisor, '')
                FROM qa_pairs qa
                LEFT JOIN categories c ON qa.category_id = c.id
            """))
            
            db.session.commit()
            logger.info("FTS index rebuilt successfully")
            
        except Exception as e:
            logger.error(f"Failed to rebuild FTS index: {str(e)}")
    
    @search_cache(ttl=300)  # 缓存搜索结果5分钟
    def search(self, query: str, category_ids: List[int] = None, 
               advisor: str = None, page: int = 1, per_page: int = 20,
               sort_by: str = 'relevance') -> SearchResult:
        """
        执行搜索
        
        Args:
            query: 搜索关键词
            category_ids: 分类ID列表
            advisor: 回答者筛选
            page: 页码
            per_page: 每页数量
            sort_by: 排序方式 ('relevance', 'time', 'confidence')
        
        Returns:
            SearchResult: 搜索结果
        """
        import time
        start_time = time.time()
        
        try:
            # 预处理查询
            processed_query = self._process_query(query)
            
            if self.fts_enabled and processed_query:
                # 使用FTS5搜索
                qa_pairs, total_count = self._fts_search(
                    processed_query, category_ids, advisor, page, per_page, sort_by
                )
            else:
                # 使用LIKE搜索作为后备
                qa_pairs, total_count = self._like_search(
                    query, category_ids, advisor, page, per_page, sort_by
                )
            
            # 计算页数
            pages = (total_count + per_page - 1) // per_page
            
            # 生成搜索建议
            suggestions = self._generate_suggestions(query) if query else []
            
            search_time = time.time() - start_time
            
            return SearchResult(
                qa_pairs=qa_pairs,
                total_count=total_count,
                page=page,
                per_page=per_page,
                pages=pages,
                query=query,
                search_time=search_time,
                suggestions=suggestions
            )
            
        except Exception as e:
            logger.error(f"Search failed: {str(e)}")
            return SearchResult(
                qa_pairs=[],
                total_count=0,
                page=page,
                per_page=per_page,
                pages=0,
                query=query,
                search_time=time.time() - start_time,
                suggestions=[]
            )
    
    def _process_query(self, query: str) -> str:
        """处理搜索查询"""
        if not query:
            return ""
        
        # 清理查询
        query = query.strip()
        if len(query) < 1:
            return ""
        
        # 中文分词
        try:
            words = jieba.lcut_for_search(query)
            # 过滤停用词和长度过短的词
            words = [word.strip() for word in words 
                    if len(word.strip()) >= 1 and word not in self.stop_words]
            
            # 添加同义词
            expanded_words = set(words)
            for word in words:
                if word in self.synonyms:
                    expanded_words.update(self.synonyms[word])
            
            return ' '.join(expanded_words)
            
        except Exception as e:
            logger.debug(f"Failed to process query with jieba: {str(e)}")
            return query
    
    def _fts_search(self, query: str, category_ids: List[int], advisor: str,
                   page: int, per_page: int, sort_by: str) -> Tuple[List[QAPair], int]:
        """FTS5全文搜索"""
        try:
            # 构建FTS查询
            fts_query = self._build_fts_query(query)
            
            # 优化：使用CTE和单一查询同时获取数据和计数
            base_sql = """
                WITH search_results AS (
                    SELECT qa.id, qa.question, qa.answer, qa.category_id, qa.asker, qa.advisor,
                           qa.confidence, qa.source_file, qa.original_context, qa.created_at, 
                           qa.updated_at, c.name as category_name,
                           bm25(qa_pairs_fts) as rank
                    FROM qa_pairs_fts fts
                    JOIN qa_pairs qa ON qa.id = fts.rowid
                    LEFT JOIN categories c ON qa.category_id = c.id
                    WHERE qa_pairs_fts MATCH ?
            """
            
            params = [fts_query]
            
            # 添加筛选条件
            if category_ids:
                placeholders = ','.join(['?' for _ in category_ids])
                base_sql += f" AND qa.category_id IN ({placeholders})"
                params.extend(category_ids)
            
            if advisor:
                base_sql += " AND qa.advisor = ?"
                params.append(advisor)
            
            base_sql += """
                ),
                total_count AS (
                    SELECT COUNT(*) as total FROM search_results
                )
                SELECT sr.*, tc.total
                FROM search_results sr
                CROSS JOIN total_count tc
            """
            
            # 添加排序
            if sort_by == 'relevance':
                base_sql += " ORDER BY sr.rank DESC"
            elif sort_by == 'time':
                base_sql += " ORDER BY sr.created_at DESC"
            elif sort_by == 'confidence':
                base_sql += " ORDER BY sr.confidence DESC, sr.created_at DESC"
            else:
                base_sql += " ORDER BY sr.rank DESC"
            
            # 添加分页
            offset = (page - 1) * per_page
            base_sql += " LIMIT ? OFFSET ?"
            params.extend([per_page, offset])
            
            # 执行单一查询获取所有数据
            results = db.session.execute(text(base_sql), params).fetchall()
            
            if not results:
                return [], 0
            
            total_count = results[0][-1]  # 最后一列是total
            
            # 直接构造QAPair对象，避免额外数据库查询
            qa_pairs = []
            for row in results:
                qa = QAPair()
                qa.id = row[0]
                qa.question = row[1]
                qa.answer = row[2]
                qa.category_id = row[3]
                qa.asker = row[4]
                qa.advisor = row[5]
                qa.confidence = row[6]
                qa.source_file = row[7]
                qa.original_context = row[8]
                qa.created_at = row[9]
                qa.updated_at = row[10]
                # 创建category对象以避免懒加载
                if row[11]:  # category_name
                    from app.models import Category
                    category = Category()
                    category.id = row[3]
                    category.name = row[11]
                    qa.category = category
                qa_pairs.append(qa)
            
            return qa_pairs, total_count
            
        except Exception as e:
            logger.error(f"FTS search failed: {str(e)}")
            # 降级到LIKE搜索
            return self._like_search(query, category_ids, advisor, page, per_page, sort_by)
    
    def _build_fts_query(self, query: str) -> str:
        """构建FTS查询字符串"""
        words = query.split()
        if not words:
            return ""
        
        # 对每个词添加前缀匹配和全词匹配
        fts_terms = []
        for word in words:
            if len(word) >= 2:
                # 使用前缀匹配和全词匹配的组合
                fts_terms.append(f'("{word}" OR {word}*)')
        
        return ' AND '.join(fts_terms) if fts_terms else query
    
    def _like_search(self, query: str, category_ids: List[int], advisor: str,
                    page: int, per_page: int, sort_by: str) -> Tuple[List[QAPair], int]:
        """LIKE搜索作为后备"""
        # 构建基础查询
        qa_query = QAPair.query
        
        # 关键词搜索
        if query:
            search_filter = db.or_(
                QAPair.question.contains(query),
                QAPair.answer.contains(query)
            )
            qa_query = qa_query.filter(search_filter)
        
        # 分类筛选
        if category_ids:
            qa_query = qa_query.filter(QAPair.category_id.in_(category_ids))
        
        # 回答者筛选
        if advisor:
            qa_query = qa_query.filter(QAPair.advisor == advisor)
        
        # 排序
        if sort_by == 'time':
            qa_query = qa_query.order_by(QAPair.created_at.desc())
        elif sort_by == 'confidence':
            qa_query = qa_query.order_by(QAPair.confidence.desc(), QAPair.created_at.desc())
        else:  # relevance or default
            if query:
                # 简单的相关性排序：优先匹配问题的结果
                qa_query = qa_query.order_by(
                    db.case(
                        (QAPair.question.contains(query), 1),
                        else_=2
                    ),
                    QAPair.created_at.desc()
                )
            else:
                qa_query = qa_query.order_by(QAPair.created_at.desc())
        
        # 分页
        pagination = qa_query.paginate(
            page=page, 
            per_page=per_page, 
            error_out=False
        )
        
        return pagination.items, pagination.total
    
    def _generate_suggestions(self, query: str) -> List[str]:
        """生成搜索建议"""
        if not query or len(query) < 2:
            return []
        
        try:
            suggestions = []
            
            # 基于分类的建议
            categories = Category.query.all()
            for cat in categories:
                if query in cat.name or cat.name in query:
                    suggestions.append(f"{query} {cat.name}")
            
            # 基于高频词的建议
            common_terms = ['如何', '什么', '为什么', '怎么', '价格', '费用', '使用', '设置', '问题', '错误']
            for term in common_terms:
                if term not in query:
                    suggestions.append(f"{query} {term}")
            
            return suggestions[:5]  # 最多返回5个建议
            
        except Exception as e:
            logger.debug(f"Failed to generate suggestions: {str(e)}")
            return []
    
    @category_cache(ttl=600)  # 缓存热门搜索10分钟
    def get_popular_searches(self, limit: int = 10) -> List[Dict[str, Any]]:
        """获取热门搜索（模拟实现）"""
        from app.utils.cache import cached
        
        @cached(ttl=600, key_prefix='popular_searches_')  # 缓存10分钟
        def _get_popular_keywords(limit: int):
            try:
                # 基于问题中的关键词统计 - 优化：增加样本量和缓存
                popular_keywords = []
                
                # 从问题中提取常见关键词 - 优化：增加到500条记录以获得更好的统计结果
                result = db.session.execute(text("""
                    SELECT question FROM qa_pairs 
                    WHERE question IS NOT NULL AND LENGTH(question) > 5
                    ORDER BY confidence DESC, created_at DESC 
                    LIMIT 500
                """)).fetchall()
                
                keyword_count = {}
                for row in result:
                    question = row[0]
                    # 使用jieba进行更精确的关键词提取
                    try:
                        words = jieba.lcut_for_search(question)
                        for word in words:
                            word = word.strip()
                            if len(word) >= 2 and word not in self.stop_words:
                                keyword_count[word] = keyword_count.get(word, 0) + 1
                    except:
                        # 降级到正则表达式提取
                        words = re.findall(r'[\u4e00-\u9fff]+', question)
                        for word in words:
                            if len(word) >= 2 and word not in self.stop_words:
                                keyword_count[word] = keyword_count.get(word, 0) + 1
                
                # 排序并返回热门关键词 - 优化：过滤低频词
                sorted_keywords = sorted(
                    [(k, v) for k, v in keyword_count.items() if v >= 2], 
                    key=lambda x: x[1], 
                    reverse=True
                )
                
                for keyword, count in sorted_keywords[:limit]:
                    popular_keywords.append({
                        'keyword': keyword,
                        'count': count,
                        'suggestion': f"搜索关于{keyword}的问题"
                    })
                
                return popular_keywords
                
            except Exception as e:
                logger.error(f"Failed to get popular searches: {str(e)}")
                return []
        
        return _get_popular_keywords(limit)
    
    def get_search_statistics(self) -> Dict[str, Any]:
        """获取搜索统计信息"""
        try:
            total_qa = QAPair.query.count()
            
            # 按分类统计
            category_stats = db.session.query(
                Category.name,
                func.count(QAPair.id).label('count')
            ).outerjoin(QAPair).group_by(Category.id).all()
            
            # FTS状态
            fts_status = {
                'enabled': self.fts_enabled,
                'table_exists': False,
                'record_count': 0
            }
            
            if self.fts_enabled:
                try:
                    result = db.session.execute(text(
                        "SELECT COUNT(*) FROM qa_pairs_fts"
                    )).fetchone()
                    fts_status['table_exists'] = True
                    fts_status['record_count'] = result[0] if result else 0
                except:
                    pass
            
            return {
                'total_qa_pairs': total_qa,
                'category_distribution': [
                    {'category': stat[0], 'count': stat[1]} 
                    for stat in category_stats
                ],
                'fts_status': fts_status,
                'search_capabilities': {
                    'full_text_search': self.fts_enabled,
                    'chinese_segmentation': True,
                    'synonym_expansion': True,
                    'category_filtering': True,
                    'advisor_filtering': True
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get search statistics: {str(e)}")
            return {
                'total_qa_pairs': 0,
                'error': str(e)
            }
    
    def update_fts_record(self, qa_pair: QAPair, operation: str = 'update'):
        """更新FTS记录"""
        if not self.fts_enabled:
            return
        
        try:
            if operation == 'insert':
                db.session.execute(text("""
                    INSERT INTO qa_pairs_fts(rowid, question, answer, category_name, advisor)
                    SELECT ?, ?, ?, COALESCE(c.name, ''), COALESCE(?, '')
                    FROM categories c WHERE c.id = ?
                """), [qa_pair.id, qa_pair.question, qa_pair.answer, qa_pair.advisor, qa_pair.category_id])
                
            elif operation == 'update':
                db.session.execute(text("""
                    UPDATE qa_pairs_fts SET 
                        question = ?, answer = ?, 
                        category_name = COALESCE((SELECT name FROM categories WHERE id = ?), ''),
                        advisor = COALESCE(?, '')
                    WHERE rowid = ?
                """), [qa_pair.question, qa_pair.answer, qa_pair.category_id, qa_pair.advisor, qa_pair.id])
                
            elif operation == 'delete':
                db.session.execute(text(
                    "DELETE FROM qa_pairs_fts WHERE rowid = ?"
                ), [qa_pair.id])
            
            db.session.commit()
            
        except Exception as e:
            logger.error(f"Failed to update FTS record: {str(e)}")
    
    def rebuild_index(self):
        """重建搜索索引"""
        try:
            self._rebuild_fts_index()
            return {
                'success': True,
                'message': 'Search index rebuilt successfully'
            }
        except Exception as e:
            logger.error(f"Failed to rebuild search index: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }