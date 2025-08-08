"""
性能测试工具 - 系统基准测试和性能回归检测
"""
import time
import json
import logging
import statistics
import concurrent.futures
from datetime import datetime, timedelta
from typing import Dict, List, Any, Callable, Optional, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
import psutil
import tempfile
import shutil

from app import db, create_app
from app.models import QAPair, Category, UploadHistory
from app.services.search_service import SearchService
from app.services.optimized_file_processor import OptimizedFileProcessor
from app.utils.memory_monitor import get_memory_monitor

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """性能测量指标"""
    operation: str
    duration_ms: float
    memory_before_mb: float
    memory_after_mb: float
    memory_peak_mb: float
    cpu_percent: float
    success: bool
    error: Optional[str] = None
    additional_data: Optional[Dict[str, Any]] = None


@dataclass
class BenchmarkResult:
    """基准测试结果"""
    test_name: str
    metrics: List[PerformanceMetrics]
    summary: Dict[str, Any]
    timestamp: datetime


class PerformanceTester:
    """性能测试器"""
    
    def __init__(self, app=None):
        self.app = app or create_app()
        self.memory_monitor = get_memory_monitor()
        self.search_service = SearchService()
        self.file_processor = OptimizedFileProcessor()
        
        # 测试配置
        self.test_iterations = 5
        self.warmup_iterations = 2
        self.timeout_seconds = 300
        
        # 基准数据存储
        self.benchmark_results: List[BenchmarkResult] = []
        self.baseline_metrics: Dict[str, Dict] = {}
    
    def measure_performance(self, operation_name: str, operation_func: Callable, 
                          *args, **kwargs) -> PerformanceMetrics:
        """
        测量单个操作的性能
        
        Args:
            operation_name: 操作名称
            operation_func: 操作函数
            *args, **kwargs: 函数参数
        
        Returns:
            PerformanceMetrics: 性能指标
        """
        # 获取初始状态
        process = psutil.Process()
        memory_before = self.memory_monitor.get_current_snapshot().rss_mb
        cpu_before = process.cpu_percent()
        
        start_time = time.perf_counter()
        success = True
        error = None
        additional_data = {}
        memory_peak = memory_before
        
        try:
            # 监控内存峰值
            memory_samples = [memory_before]
            
            def memory_monitor_thread():
                for _ in range(100):  # 最多监控10秒
                    time.sleep(0.1)
                    current = self.memory_monitor.get_current_snapshot().rss_mb
                    memory_samples.append(current)
            
            # 启动内存监控线程
            import threading
            monitor_thread = threading.Thread(target=memory_monitor_thread, daemon=True)
            monitor_thread.start()
            
            # 执行操作
            result = operation_func(*args, **kwargs)
            
            # 如果返回结果包含额外数据
            if isinstance(result, dict):
                additional_data = result
            elif hasattr(result, '__dict__'):
                additional_data = asdict(result) if hasattr(result, '__dataclass_fields__') else result.__dict__
            
        except Exception as e:
            success = False
            error = str(e)
            logger.error(f"Performance test failed for {operation_name}: {error}")
        
        finally:
            end_time = time.perf_counter()
            
            # 等待内存监控完成
            monitor_thread.join(timeout=1)
            memory_peak = max(memory_samples) if memory_samples else memory_before
            
            # 获取最终状态
            memory_after = self.memory_monitor.get_current_snapshot().rss_mb
            cpu_after = process.cpu_percent()
            cpu_percent = max(cpu_after - cpu_before, 0)
        
        duration_ms = (end_time - start_time) * 1000
        
        return PerformanceMetrics(
            operation=operation_name,
            duration_ms=duration_ms,
            memory_before_mb=memory_before,
            memory_after_mb=memory_after,
            memory_peak_mb=memory_peak,
            cpu_percent=cpu_percent,
            success=success,
            error=error,
            additional_data=additional_data
        )
    
    def run_benchmark_suite(self) -> List[BenchmarkResult]:
        """运行完整的基准测试套件"""
        logger.info("Starting comprehensive benchmark suite")
        
        with self.app.app_context():
            benchmark_results = [
                self.benchmark_database_operations(),
                self.benchmark_search_operations(),
                self.benchmark_file_processing(),
                self.benchmark_memory_operations(),
                self.benchmark_concurrent_operations()
            ]
        
        self.benchmark_results.extend(benchmark_results)
        
        # 生成性能报告
        self.generate_performance_report()
        
        logger.info("Benchmark suite completed")
        return benchmark_results
    
    def benchmark_database_operations(self) -> BenchmarkResult:
        """数据库操作基准测试"""
        logger.info("Running database operations benchmark")
        
        metrics = []
        
        # 准备测试数据
        test_categories = [
            Category(name=f"测试分类_{i}", description=f"测试分类描述_{i}")
            for i in range(5)
        ]
        
        with self.app.app_context():
            # 测试批量插入
            for _ in range(self.test_iterations):
                metric = self.measure_performance(
                    "database_bulk_insert_categories",
                    self._test_bulk_insert_categories,
                    test_categories.copy()
                )
                metrics.append(metric)
            
            # 测试单个查询
            for _ in range(self.test_iterations):
                metric = self.measure_performance(
                    "database_single_query",
                    self._test_single_query
                )
                metrics.append(metric)
            
            # 测试复杂查询
            for _ in range(self.test_iterations):
                metric = self.measure_performance(
                    "database_complex_query",
                    self._test_complex_query
                )
                metrics.append(metric)
            
            # 测试批量更新
            for _ in range(self.test_iterations):
                metric = self.measure_performance(
                    "database_bulk_update",
                    self._test_bulk_update
                )
                metrics.append(metric)
        
        # 计算统计信息
        summary = self._calculate_benchmark_summary(metrics, "database_operations")
        
        return BenchmarkResult(
            test_name="database_operations",
            metrics=metrics,
            summary=summary,
            timestamp=datetime.utcnow()
        )
    
    def benchmark_search_operations(self) -> BenchmarkResult:
        """搜索操作基准测试"""
        logger.info("Running search operations benchmark")
        
        metrics = []
        
        # 测试查询
        search_queries = [
            "如何使用产品",
            "价格费用",
            "技术支持联系方式",
            "安装配置步骤",
            "常见问题解答"
        ]
        
        with self.app.app_context():
            for query in search_queries:
                for _ in range(self.test_iterations):
                    metric = self.measure_performance(
                        f"search_query_{query[:5]}",
                        self._test_search_query,
                        query
                    )
                    metrics.append(metric)
            
            # 测试分页搜索
            for page in range(1, 6):
                metric = self.measure_performance(
                    f"search_pagination_page_{page}",
                    self._test_paginated_search,
                    "产品", page
                )
                metrics.append(metric)
            
            # 测试高级搜索
            for _ in range(self.test_iterations):
                metric = self.measure_performance(
                    "search_advanced",
                    self._test_advanced_search
                )
                metrics.append(metric)
        
        summary = self._calculate_benchmark_summary(metrics, "search_operations")
        
        return BenchmarkResult(
            test_name="search_operations",
            metrics=metrics,
            summary=summary,
            timestamp=datetime.utcnow()
        )
    
    def benchmark_file_processing(self) -> BenchmarkResult:
        """文件处理基准测试"""
        logger.info("Running file processing benchmark")
        
        metrics = []
        
        # 创建测试文件
        test_files = self._create_test_files()
        
        try:
            with self.app.app_context():
                for file_path, file_size in test_files:
                    for _ in range(max(1, self.test_iterations // 2)):  # 文件处理测试减少迭代次数
                        metric = self.measure_performance(
                            f"file_processing_{file_size}KB",
                            self._test_file_processing,
                            file_path
                        )
                        metrics.append(metric)
        
        finally:
            # 清理测试文件
            self._cleanup_test_files(test_files)
        
        summary = self._calculate_benchmark_summary(metrics, "file_processing")
        
        return BenchmarkResult(
            test_name="file_processing",
            metrics=metrics,
            summary=summary,
            timestamp=datetime.utcnow()
        )
    
    def benchmark_memory_operations(self) -> BenchmarkResult:
        """内存操作基准测试"""
        logger.info("Running memory operations benchmark")
        
        metrics = []
        
        # 测试大数据量操作
        data_sizes = [1000, 5000, 10000]
        
        for size in data_sizes:
            for _ in range(self.test_iterations):
                metric = self.measure_performance(
                    f"memory_large_dataset_{size}",
                    self._test_large_dataset_processing,
                    size
                )
                metrics.append(metric)
        
        # 测试内存清理
        for _ in range(self.test_iterations):
            metric = self.measure_performance(
                "memory_cleanup",
                self._test_memory_cleanup
            )
            metrics.append(metric)
        
        # 测试缓存操作
        for _ in range(self.test_iterations):
            metric = self.measure_performance(
                "memory_cache_operations",
                self._test_cache_operations
            )
            metrics.append(metric)
        
        summary = self._calculate_benchmark_summary(metrics, "memory_operations")
        
        return BenchmarkResult(
            test_name="memory_operations",
            metrics=metrics,
            summary=summary,
            timestamp=datetime.utcnow()
        )
    
    def benchmark_concurrent_operations(self) -> BenchmarkResult:
        """并发操作基准测试"""
        logger.info("Running concurrent operations benchmark")
        
        metrics = []
        
        # 测试并发搜索
        for thread_count in [2, 4, 8]:
            for _ in range(max(1, self.test_iterations // 2)):
                metric = self.measure_performance(
                    f"concurrent_search_{thread_count}_threads",
                    self._test_concurrent_search,
                    thread_count
                )
                metrics.append(metric)
        
        # 测试并发数据库操作
        for thread_count in [2, 4, 8]:
            for _ in range(max(1, self.test_iterations // 2)):
                metric = self.measure_performance(
                    f"concurrent_db_ops_{thread_count}_threads",
                    self._test_concurrent_db_operations,
                    thread_count
                )
                metrics.append(metric)
        
        summary = self._calculate_benchmark_summary(metrics, "concurrent_operations")
        
        return BenchmarkResult(
            test_name="concurrent_operations",
            metrics=metrics,
            summary=summary,
            timestamp=datetime.utcnow()
        )
    
    # 测试辅助方法
    def _test_bulk_insert_categories(self, categories):
        """测试批量插入分类"""
        for cat in categories:
            db.session.merge(cat)  # 使用merge避免重复
        db.session.commit()
        return {"categories_inserted": len(categories)}
    
    def _test_single_query(self):
        """测试单个查询"""
        result = Category.query.first()
        return {"found": result is not None}
    
    def _test_complex_query(self):
        """测试复杂查询"""
        result = db.session.query(QAPair).join(Category).filter(
            QAPair.confidence > 0.5
        ).order_by(QAPair.created_at.desc()).limit(10).all()
        return {"results_count": len(result)}
    
    def _test_bulk_update(self):
        """测试批量更新"""
        qa_pairs = QAPair.query.limit(100).all()
        for qa in qa_pairs:
            qa.confidence = min(1.0, qa.confidence + 0.01)
        db.session.commit()
        return {"updated_count": len(qa_pairs)}
    
    def _test_search_query(self, query):
        """测试搜索查询"""
        result = self.search_service.search(query, page=1, per_page=20)
        return {
            "results_count": result.total_count,
            "search_time": result.search_time
        }
    
    def _test_paginated_search(self, query, page):
        """测试分页搜索"""
        result = self.search_service.search(query, page=page, per_page=10)
        return {
            "page": page,
            "results_count": len(result.qa_pairs),
            "total_count": result.total_count
        }
    
    def _test_advanced_search(self):
        """测试高级搜索"""
        result = self.search_service.search(
            "产品", 
            category_ids=[1, 2], 
            sort_by='confidence',
            page=1,
            per_page=50
        )
        return {
            "results_count": result.total_count,
            "search_time": result.search_time
        }
    
    def _test_file_processing(self, file_path):
        """测试文件处理"""
        # 创建临时上传记录
        upload_record = UploadHistory(
            filename=file_path.name,
            file_size=file_path.stat().st_size,
            file_hash="test_hash",
            status='processing'
        )
        db.session.add(upload_record)
        db.session.commit()
        
        # 处理文件
        result = self.file_processor.process_file_optimized(file_path, upload_record)
        
        return {
            "success": result.success,
            "extracted_count": result.total_extracted,
            "saved_count": result.total_saved,
            "processing_time": result.processing_time
        }
    
    def _test_large_dataset_processing(self, size):
        """测试大数据集处理"""
        # 模拟大数据集处理
        data = [{"id": i, "content": f"测试内容_{i}"} for i in range(size)]
        
        # 处理数据
        processed = []
        for item in data:
            processed.append({
                "id": item["id"],
                "processed_content": item["content"].upper(),
                "length": len(item["content"])
            })
        
        return {"processed_count": len(processed)}
    
    def _test_memory_cleanup(self):
        """测试内存清理"""
        import gc
        
        # 创建一些临时数据
        temp_data = [f"临时数据_{i}" * 1000 for i in range(1000)]
        
        # 清理内存
        del temp_data
        collected = gc.collect()
        
        return {"objects_collected": collected}
    
    def _test_cache_operations(self):
        """测试缓存操作"""
        from app.utils.cache import MultiLevelCache
        
        cache = MultiLevelCache()
        
        # 测试缓存操作
        for i in range(100):
            cache.set(f"key_{i}", f"value_{i}")
        
        hit_count = 0
        for i in range(100):
            if cache.get(f"key_{i}") is not None:
                hit_count += 1
        
        return {"cache_hit_rate": hit_count / 100.0}
    
    def _test_concurrent_search(self, thread_count):
        """测试并发搜索"""
        queries = ["产品", "价格", "支持", "配置", "问题"] * 10
        results = []
        
        def search_worker(query):
            return self.search_service.search(query, page=1, per_page=10)
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=thread_count) as executor:
            future_to_query = {executor.submit(search_worker, query): query for query in queries}
            
            for future in concurrent.futures.as_completed(future_to_query):
                try:
                    result = future.result(timeout=30)
                    results.append(result)
                except Exception as e:
                    logger.error(f"Concurrent search failed: {str(e)}")
        
        return {
            "total_searches": len(queries),
            "successful_searches": len(results),
            "success_rate": len(results) / len(queries)
        }
    
    def _test_concurrent_db_operations(self, thread_count):
        """测试并发数据库操作"""
        operations_count = 50
        results = []
        
        def db_worker(operation_id):
            # 模拟数据库操作
            categories = Category.query.limit(5).all()
            return len(categories)
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=thread_count) as executor:
            future_to_id = {executor.submit(db_worker, i): i for i in range(operations_count)}
            
            for future in concurrent.futures.as_completed(future_to_id):
                try:
                    result = future.result(timeout=10)
                    results.append(result)
                except Exception as e:
                    logger.error(f"Concurrent DB operation failed: {str(e)}")
        
        return {
            "total_operations": operations_count,
            "successful_operations": len(results),
            "success_rate": len(results) / operations_count
        }
    
    def _create_test_files(self) -> List[Tuple[Path, int]]:
        """创建测试文件"""
        test_files = []
        temp_dir = Path(tempfile.gettempdir()) / "chatlog_performance_tests"
        temp_dir.mkdir(exist_ok=True)
        
        # 创建不同大小的测试文件
        file_configs = [
            (100, "small"),    # 100条消息
            (1000, "medium"),  # 1000条消息
            (5000, "large")    # 5000条消息
        ]
        
        for message_count, size_name in file_configs:
            messages = []
            for i in range(message_count):
                messages.append({
                    "sender": f"用户_{i % 10}",
                    "content": f"这是第{i}条测试消息，用于性能测试。内容长度适中，包含中文字符。",
                    "timestamp": datetime.utcnow().isoformat(),
                    "type": "text"
                })
            
            test_data = {
                "messages": messages,
                "metadata": {
                    "export_time": datetime.utcnow().isoformat(),
                    "message_count": message_count,
                    "test_file": True
                }
            }
            
            file_path = temp_dir / f"test_{size_name}_{message_count}.json"
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(test_data, f, ensure_ascii=False, indent=2)
            
            file_size_kb = file_path.stat().st_size // 1024
            test_files.append((file_path, file_size_kb))
            
            logger.info(f"Created test file: {file_path} ({file_size_kb}KB)")
        
        return test_files
    
    def _cleanup_test_files(self, test_files: List[Tuple[Path, int]]):
        """清理测试文件"""
        for file_path, _ in test_files:
            try:
                if file_path.exists():
                    file_path.unlink()
                # 清理父目录（如果为空）
                if file_path.parent.exists() and not any(file_path.parent.iterdir()):
                    file_path.parent.rmdir()
            except Exception as e:
                logger.warning(f"Failed to cleanup test file {file_path}: {str(e)}")
    
    def _calculate_benchmark_summary(self, metrics: List[PerformanceMetrics], test_category: str) -> Dict[str, Any]:
        """计算基准测试统计摘要"""
        if not metrics:
            return {}
        
        # 按操作分组
        operations = {}
        for metric in metrics:
            if metric.operation not in operations:
                operations[metric.operation] = []
            operations[metric.operation].append(metric)
        
        # 计算每个操作的统计信息
        operation_stats = {}
        for op_name, op_metrics in operations.items():
            successful_metrics = [m for m in op_metrics if m.success]
            
            if successful_metrics:
                durations = [m.duration_ms for m in successful_metrics]
                memory_usage = [m.memory_peak_mb - m.memory_before_mb for m in successful_metrics]
                
                operation_stats[op_name] = {
                    "iterations": len(op_metrics),
                    "success_rate": len(successful_metrics) / len(op_metrics),
                    "duration_ms": {
                        "min": min(durations),
                        "max": max(durations),
                        "mean": statistics.mean(durations),
                        "median": statistics.median(durations),
                        "std_dev": statistics.stdev(durations) if len(durations) > 1 else 0
                    },
                    "memory_usage_mb": {
                        "min": min(memory_usage),
                        "max": max(memory_usage),
                        "mean": statistics.mean(memory_usage),
                        "median": statistics.median(memory_usage)
                    }
                }
        
        # 总体统计
        all_successful = [m for m in metrics if m.success]
        total_success_rate = len(all_successful) / len(metrics) if metrics else 0
        
        return {
            "test_category": test_category,
            "total_operations": len(metrics),
            "success_rate": total_success_rate,
            "operation_stats": operation_stats,
            "overall_performance": {
                "avg_duration_ms": statistics.mean([m.duration_ms for m in all_successful]) if all_successful else 0,
                "avg_memory_usage_mb": statistics.mean([m.memory_peak_mb - m.memory_before_mb for m in all_successful]) if all_successful else 0
            }
        }
    
    def generate_performance_report(self) -> Dict[str, Any]:
        """生成性能报告"""
        if not self.benchmark_results:
            return {"error": "No benchmark results available"}
        
        report = {
            "report_timestamp": datetime.utcnow().isoformat(),
            "system_info": self._get_system_info(),
            "test_summary": {
                "total_test_suites": len(self.benchmark_results),
                "test_suites": [result.test_name for result in self.benchmark_results]
            },
            "benchmark_results": []
        }
        
        # 处理每个基准测试结果
        for result in self.benchmark_results:
            report["benchmark_results"].append({
                "test_name": result.test_name,
                "timestamp": result.timestamp.isoformat(),
                "summary": result.summary,
                "performance_grade": self._calculate_performance_grade(result.summary)
            })
        
        # 生成性能建议
        report["performance_recommendations"] = self._generate_performance_recommendations()
        
        # 保存报告
        self._save_performance_report(report)
        
        return report
    
    def _get_system_info(self) -> Dict[str, Any]:
        """获取系统信息"""
        return {
            "cpu_count": psutil.cpu_count(),
            "memory_total_gb": psutil.virtual_memory().total / (1024**3),
            "python_version": ".".join(map(str, __import__('sys').version_info[:3])),
            "platform": __import__('platform').platform()
        }
    
    def _calculate_performance_grade(self, summary: Dict[str, Any]) -> str:
        """计算性能等级"""
        try:
            success_rate = summary.get("success_rate", 0)
            overall_perf = summary.get("overall_performance", {})
            avg_duration = overall_perf.get("avg_duration_ms", float('inf'))
            
            # 基于成功率和平均响应时间评级
            if success_rate >= 0.95 and avg_duration <= 100:
                return "A+"
            elif success_rate >= 0.9 and avg_duration <= 200:
                return "A"
            elif success_rate >= 0.85 and avg_duration <= 500:
                return "B"
            elif success_rate >= 0.8 and avg_duration <= 1000:
                return "C"
            else:
                return "D"
        except:
            return "Unknown"
    
    def _generate_performance_recommendations(self) -> List[str]:
        """生成性能建议"""
        recommendations = []
        
        for result in self.benchmark_results:
            summary = result.summary
            
            # 检查成功率
            if summary.get("success_rate", 1) < 0.95:
                recommendations.append(f"提高 {result.test_name} 的操作成功率（当前: {summary.get('success_rate', 0)*100:.1f}%）")
            
            # 检查响应时间
            overall_perf = summary.get("overall_performance", {})
            avg_duration = overall_perf.get("avg_duration_ms", 0)
            if avg_duration > 1000:
                recommendations.append(f"优化 {result.test_name} 的响应时间（当前平均: {avg_duration:.1f}ms）")
            
            # 检查内存使用
            avg_memory = overall_perf.get("avg_memory_usage_mb", 0)
            if avg_memory > 50:
                recommendations.append(f"优化 {result.test_name} 的内存使用（当前平均: {avg_memory:.1f}MB）")
        
        if not recommendations:
            recommendations.append("系统性能表现良好，无特殊优化建议")
        
        return recommendations
    
    def _save_performance_report(self, report: Dict[str, Any]):
        """保存性能报告"""
        try:
            report_dir = Path("performance_reports")
            report_dir.mkdir(exist_ok=True)
            
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            report_file = report_dir / f"performance_report_{timestamp}.json"
            
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Performance report saved to {report_file}")
            
        except Exception as e:
            logger.error(f"Failed to save performance report: {str(e)}")


# 便捷函数
def run_quick_performance_test(app=None) -> Dict[str, Any]:
    """运行快速性能测试"""
    tester = PerformanceTester(app)
    tester.test_iterations = 3  # 减少迭代次数
    
    # 只运行核心测试
    with tester.app.app_context():
        results = [
            tester.benchmark_database_operations(),
            tester.benchmark_search_operations()
        ]
    
    tester.benchmark_results = results
    return tester.generate_performance_report()


def run_full_performance_test(app=None) -> Dict[str, Any]:
    """运行完整性能测试"""
    tester = PerformanceTester(app)
    return tester.run_benchmark_suite()


# 全局性能测试器实例
performance_tester = PerformanceTester()


def get_performance_tester() -> PerformanceTester:
    """获取全局性能测试器实例"""
    return performance_tester