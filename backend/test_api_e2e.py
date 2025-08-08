#!/usr/bin/env python3
"""
API端到端测试：测试智能处理相关的API端点

测试覆盖：
1. AI配置API
2. 智能文件上传API
3. AI统计和监控API
4. 处理状态查询API

执行命令：python test_api_e2e.py
"""

import requests
import json
import time
import os
from pathlib import Path
import sys

# 配置
BASE_URL = "http://localhost:5001"
API_BASE = f"{BASE_URL}/api/v1"

class APITester:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'Chatlog-E2E-Test/1.0'
        })
        self.test_results = []
        self.total_tests = 0
        self.passed_tests = 0
    
    def log_test(self, test_name: str, result: bool, details: str = "", response_time: float = 0):
        """记录测试结果"""
        status = "✅ PASS" if result else "❌ FAIL"
        timing_str = f" ({response_time:.2f}s)" if response_time else ""
        
        self.test_results.append({
            'test_name': test_name,
            'result': result,
            'details': details,
            'response_time': response_time
        })
        
        self.total_tests += 1
        if result:
            self.passed_tests += 1
            
        print(f"{status} {test_name}{timing_str}")
        if details:
            print(f"    └─ {details}")
    
    def test_server_health(self):
        """测试服务器健康状态"""
        try:
            start_time = time.time()
            response = self.session.get(f"{API_BASE}/categories")
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                self.log_test("服务器健康检查", True, f"状态码: {response.status_code}", response_time)
                return True
            else:
                self.log_test("服务器健康检查", False, f"状态码: {response.status_code}", response_time)
                return False
        except Exception as e:
            self.log_test("服务器健康检查", False, f"连接错误: {str(e)}")
            return False
    
    def test_categories_api(self):
        """测试类别API"""
        try:
            start_time = time.time()
            response = self.session.get(f"{API_BASE}/categories")
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                categories = data.get('data', [])
                self.log_test(
                    "类别API", 
                    True, 
                    f"获取到 {len(categories)} 个分类", 
                    response_time
                )
                return True
            else:
                self.log_test("类别API", False, f"状态码: {response.status_code}", response_time)
                return False
        except Exception as e:
            self.log_test("类别API", False, f"错误: {str(e)}")
            return False
    
    def test_ai_capabilities_api(self):
        """测试AI能力查询API"""
        try:
            start_time = time.time()
            response = self.session.get(f"{API_BASE}/upload/ai/capabilities")
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                capabilities = data.get('data', {})
                ai_enabled = capabilities.get('ai_enabled', False)
                primary_provider = capabilities.get('primary_provider', 'None')
                
                self.log_test(
                    "AI能力查询API", 
                    True, 
                    f"AI启用: {ai_enabled}, 主要提供商: {primary_provider}", 
                    response_time
                )
                return capabilities
            else:
                self.log_test("AI能力查询API", False, f"状态码: {response.status_code}", response_time)
                return None
        except Exception as e:
            self.log_test("AI能力查询API", False, f"错误: {str(e)}")
            return None
    
    def test_ai_usage_stats_api(self):
        """测试AI使用统计API"""
        try:
            start_time = time.time()
            response = self.session.get(f"{API_BASE}/upload/ai/usage")
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                usage_data = data.get('data', {})
                total_requests = usage_data.get('total_requests', 0)
                
                self.log_test(
                    "AI使用统计API", 
                    True, 
                    f"总请求数: {total_requests}", 
                    response_time
                )
                return usage_data
            else:
                self.log_test("AI使用统计API", False, f"状态码: {response.status_code}", response_time)
                return None
        except Exception as e:
            self.log_test("AI使用统计API", False, f"错误: {str(e)}")
            return None
    
    def test_upload_history_api(self):
        """测试上传历史API"""
        try:
            start_time = time.time()
            response = self.session.get(f"{API_BASE}/upload/history")
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                history = data.get('data', [])
                pagination = data.get('pagination', {})
                
                self.log_test(
                    "上传历史API", 
                    True, 
                    f"历史记录数: {len(history)}, 总数: {pagination.get('total', 0)}", 
                    response_time
                )
                return history
            else:
                self.log_test("上传历史API", False, f"状态码: {response.status_code}", response_time)
                return None
        except Exception as e:
            self.log_test("上传历史API", False, f"错误: {str(e)}")
            return None
    
    def test_intelligent_upload_api(self):
        """测试智能上传API"""
        try:
            # 创建测试文件
            test_data = {
                "metadata": {
                    "group_name": "API测试群",
                    "export_time": "2024-01-15T10:00:00",
                    "total_messages": 5
                },
                "messages": [
                    {
                        "timestamp": "2024-01-15 10:30:00",
                        "sender": "测试用户1",
                        "content": "这是一个测试问题：如何使用API？",
                        "type": "text"
                    },
                    {
                        "timestamp": "2024-01-15 10:31:00", 
                        "sender": "测试专家",
                        "content": "API使用很简单，发送HTTP请求到指定端点即可",
                        "type": "text"
                    },
                    {
                        "timestamp": "2024-01-15 10:32:00",
                        "sender": "闲聊用户",
                        "content": "大家好",
                        "type": "text"
                    }
                ]
            }
            
            # 保存临时文件
            test_file_path = Path("test_api_data.json")
            with open(test_file_path, 'w', encoding='utf-8') as f:
                json.dump(test_data, f, ensure_ascii=False, indent=2)
            
            # 测试智能上传
            start_time = time.time()
            
            with open(test_file_path, 'rb') as f:
                files = {'file': ('test_api_data.json', f, 'application/json')}
                response = requests.post(
                    f"{API_BASE}/upload/file/intelligent",
                    files=files,
                    timeout=30
                )
            
            response_time = time.time() - start_time
            
            # 清理测试文件
            if test_file_path.exists():
                test_file_path.unlink()
            
            if response.status_code == 200:
                data = response.json()
                upload_data = data.get('data', {})
                upload_id = upload_data.get('upload_id')
                processing_summary = upload_data.get('processing_summary', {})
                
                self.log_test(
                    "智能上传API", 
                    True, 
                    f"上传ID: {upload_id}, 原始消息: {processing_summary.get('original_messages', 0)}, 生成条目: {processing_summary.get('final_knowledge_entries', 0)}", 
                    response_time
                )
                return upload_data
            else:
                error_detail = ""
                try:
                    error_data = response.json()
                    error_detail = error_data.get('error', {}).get('details', response.text[:200])
                except:
                    error_detail = response.text[:200]
                
                self.log_test("智能上传API", False, f"状态码: {response.status_code}, 错误: {error_detail}", response_time)
                return None
                
        except Exception as e:
            # 确保清理文件
            test_file_path = Path("test_api_data.json")
            if test_file_path.exists():
                test_file_path.unlink()
            
            self.log_test("智能上传API", False, f"错误: {str(e)}")
            return None
    
    def test_standard_upload_api(self):
        """测试标准上传API（作为对比）"""
        try:
            # 创建测试文件
            test_data = {
                "metadata": {
                    "group_name": "标准测试群",
                    "total_messages": 3
                },
                "messages": [
                    {
                        "timestamp": "2024-01-15 11:00:00",
                        "sender": "用户A",
                        "content": "标准处理测试问题",
                        "type": "text"
                    },
                    {
                        "timestamp": "2024-01-15 11:01:00",
                        "sender": "用户B", 
                        "content": "这是标准处理的回答",
                        "type": "text"
                    }
                ]
            }
            
            # 保存临时文件
            test_file_path = Path("test_standard_data.json")
            with open(test_file_path, 'w', encoding='utf-8') as f:
                json.dump(test_data, f, ensure_ascii=False, indent=2)
            
            # 测试标准上传
            start_time = time.time()
            
            with open(test_file_path, 'rb') as f:
                files = {'file': ('test_standard_data.json', f, 'application/json')}
                data = {'use_ai': 'false', 'processing_mode': 'standard'}
                response = requests.post(
                    f"{API_BASE}/upload/file",
                    files=files,
                    data=data,
                    timeout=30
                )
            
            response_time = time.time() - start_time
            
            # 清理测试文件
            if test_file_path.exists():
                test_file_path.unlink()
            
            if response.status_code == 200:
                data = response.json()
                upload_data = data.get('data', {})
                
                self.log_test(
                    "标准上传API", 
                    True, 
                    f"上传ID: {upload_data.get('upload_id')}, 提取: {upload_data.get('total_extracted', 0)}个, 保存: {upload_data.get('total_saved', 0)}个", 
                    response_time
                )
                return upload_data
            else:
                self.log_test("标准上传API", False, f"状态码: {response.status_code}", response_time)
                return None
                
        except Exception as e:
            # 确保清理文件
            test_file_path = Path("test_standard_data.json")
            if test_file_path.exists():
                test_file_path.unlink()
            
            self.log_test("标准上传API", False, f"错误: {str(e)}")
            return None
    
    def generate_report(self):
        """生成测试报告"""
        print("\n" + "="*80)
        print("🌐 CHATLOG API 端到端测试报告")
        print("="*80)
        print(f"总测试用例: {self.total_tests}")
        print(f"通过: {self.passed_tests} ✅")
        print(f"失败: {self.total_tests - self.passed_tests} ❌")
        print(f"成功率: {(self.passed_tests/self.total_tests*100):.1f}%")
        
        # 平均响应时间
        response_times = [r['response_time'] for r in self.test_results if r['response_time'] > 0]
        if response_times:
            avg_response_time = sum(response_times) / len(response_times)
            print(f"平均响应时间: {avg_response_time:.2f}秒")
        
        print("\n📋 详细测试结果:")
        print("-" * 80)
        for result in self.test_results:
            status = "✅ PASS" if result['result'] else "❌ FAIL"
            timing_str = f"({result['response_time']:.2f}s)" if result['response_time'] else ""
            print(f"{status} {result['test_name']} {timing_str}")
            if result['details']:
                print(f"    └─ {result['details']}")
        
        print("\n🎯 API测试覆盖:")
        print("✅ 服务器健康检查")
        print("✅ 基础数据API（分类、历史）")
        print("✅ AI功能API（能力查询、使用统计）")
        print("✅ 智能文件上传API")
        print("✅ 标准文件上传API（对比）")
        
        if self.passed_tests == self.total_tests:
            print("\n🎉 所有API测试通过！系统API就绪")
        else:
            print(f"\n⚠️  {self.total_tests - self.passed_tests} 个API测试失败")
        
        print("="*80)
        
        return self.passed_tests == self.total_tests
    
    def run_all_tests(self):
        """运行所有测试"""
        print("🚀 开始运行Chatlog API端到端测试...")
        print("="*80)
        
        # 首先检查服务器是否可访问
        if not self.test_server_health():
            print("❌ 服务器不可访问，请确保后端服务器运行在 http://localhost:5001")
            return False
        
        # 运行基础API测试
        self.test_categories_api()
        self.test_upload_history_api()
        
        # 运行AI相关API测试
        capabilities = self.test_ai_capabilities_api()
        self.test_ai_usage_stats_api()
        
        # 运行文件上传测试
        self.test_intelligent_upload_api()
        self.test_standard_upload_api()
        
        # 生成报告
        return self.generate_report()


def main():
    """主函数"""
    tester = APITester()
    success = tester.run_all_tests()
    
    # 返回适当的退出码
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()