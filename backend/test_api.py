#!/usr/bin/env python3
"""
API集成测试脚本
测试微信群问答知识库系统的主要API端点
"""

import json
import requests
import time
from pathlib import Path

class APITester:
    def __init__(self, base_url="http://localhost:5000"):
        self.base_url = base_url
        self.api_base = f"{base_url}/api/v1"
        self.session = requests.Session()
        self.test_results = []
    
    def log_result(self, test_name, success, message="", details=None):
        """记录测试结果"""
        self.test_results.append({
            'test': test_name,
            'success': success,
            'message': message,
            'details': details
        })
        
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}: {message}")
        if details and not success:
            print(f"    详情: {details}")
    
    def test_health_check(self):
        """测试健康检查"""
        try:
            response = self.session.get(f"{self.api_base}/health", timeout=5)
            if response.status_code == 200:
                data = response.json()
                self.log_result("健康检查", True, f"系统状态正常: {data.get('message', '')}")
            else:
                self.log_result("健康检查", False, f"HTTP状态码: {response.status_code}")
        except Exception as e:
            self.log_result("健康检查", False, "连接失败", str(e))
    
    def test_api_info(self):
        """测试API信息"""
        try:
            response = self.session.get(f"{self.api_base}/info", timeout=5)
            if response.status_code == 200:
                data = response.json()
                self.log_result("API信息", True, f"API版本: {data.get('data', {}).get('version', 'unknown')}")
            else:
                self.log_result("API信息", False, f"HTTP状态码: {response.status_code}")
        except Exception as e:
            self.log_result("API信息", False, "请求失败", str(e))
    
    def test_categories(self):
        """测试分类接口"""
        try:
            response = self.session.get(f"{self.api_base}/categories", timeout=5)
            if response.status_code == 200:
                data = response.json()
                categories = data.get('data', [])
                self.log_result("获取分类", True, f"共{len(categories)}个分类")
                return categories
            else:
                self.log_result("获取分类", False, f"HTTP状态码: {response.status_code}")
                return []
        except Exception as e:
            self.log_result("获取分类", False, "请求失败", str(e))
            return []
    
    def test_qa_list(self):
        """测试问答列表"""
        try:
            response = self.session.get(f"{self.api_base}/qa", timeout=5)
            if response.status_code == 200:
                data = response.json()
                qa_pairs = data.get('data', [])
                total = data.get('total', 0)
                self.log_result("问答列表", True, f"共{total}条问答记录")
                return qa_pairs
            else:
                self.log_result("问答列表", False, f"HTTP状态码: {response.status_code}")
                return []
        except Exception as e:
            self.log_result("问答列表", False, "请求失败", str(e))
            return []
    
    def test_search_basic(self):
        """测试基础搜索"""
        try:
            # 测试空搜索
            response = self.session.get(f"{self.api_base}/search/", timeout=5)
            if response.status_code == 200:
                data = response.json()
                total = data.get('pagination', {}).get('total', 0)
                self.log_result("空搜索", True, f"返回{total}条结果")
            else:
                self.log_result("空搜索", False, f"HTTP状态码: {response.status_code}")
            
            # 测试关键词搜索
            response = self.session.get(f"{self.api_base}/search/?q=chatlog", timeout=5)
            if response.status_code == 200:
                data = response.json()
                total = data.get('pagination', {}).get('total', 0)
                search_time = data.get('search_info', {}).get('search_time', 0)
                self.log_result("关键词搜索", True, f"搜索'chatlog'找到{total}条结果，耗时{search_time}s")
            else:
                self.log_result("关键词搜索", False, f"HTTP状态码: {response.status_code}")
        except Exception as e:
            self.log_result("搜索功能", False, "请求失败", str(e))
    
    def test_search_suggestions(self):
        """测试搜索建议"""
        try:
            response = self.session.get(f"{self.api_base}/search/suggestions?q=如何", timeout=5)
            if response.status_code == 200:
                data = response.json()
                suggestions = data.get('data', [])
                self.log_result("搜索建议", True, f"获得{len(suggestions)}条建议")
            else:
                self.log_result("搜索建议", False, f"HTTP状态码: {response.status_code}")
        except Exception as e:
            self.log_result("搜索建议", False, "请求失败", str(e))
    
    def test_upload_history(self):
        """测试上传历史"""
        try:
            response = self.session.get(f"{self.api_base}/upload/history", timeout=5)
            if response.status_code == 200:
                data = response.json()
                uploads = data.get('data', [])
                total = data.get('pagination', {}).get('total', 0)
                self.log_result("上传历史", True, f"共{total}条上传记录")
            else:
                self.log_result("上传历史", False, f"HTTP状态码: {response.status_code}")
        except Exception as e:
            self.log_result("上传历史", False, "请求失败", str(e))
    
    def test_admin_stats(self):
        """测试管理统计"""
        try:
            response = self.session.get(f"{self.api_base}/admin/stats", timeout=10)
            if response.status_code == 200:
                data = response.json()
                stats = data.get('data', {})
                qa_stats = stats.get('qa_statistics', {})
                total_qa = qa_stats.get('total_qa', 0)
                self.log_result("管理统计", True, f"系统统计正常，共{total_qa}条问答")
            else:
                self.log_result("管理统计", False, f"HTTP状态码: {response.status_code}")
        except Exception as e:
            self.log_result("管理统计", False, "请求失败", str(e))
    
    def test_admin_health(self):
        """测试系统健康检查"""
        try:
            response = self.session.get(f"{self.api_base}/admin/health", timeout=10)
            if response.status_code == 200:
                data = response.json()
                health_data = data.get('data', {})
                overall = health_data.get('overall', 'unknown')
                components = health_data.get('components', {})
                self.log_result("系统健康", True, f"总体状态: {overall}, 组件检查: {len(components)}项")
            else:
                self.log_result("系统健康", False, f"HTTP状态码: {response.status_code}")
        except Exception as e:
            self.log_result("系统健康", False, "请求失败", str(e))
    
    def test_file_upload(self):
        """测试文件上传（创建测试JSON文件）"""
        try:
            # 创建测试JSON文件
            test_data = {
                "messages": [
                    {
                        "sender": "用户A",
                        "content": "如何使用这个系统？",
                        "timestamp": "2024-08-06 10:00:00",
                        "type": "text"
                    },
                    {
                        "sender": "管理员",
                        "content": "您可以通过上传微信聊天记录JSON文件来创建知识库，系统会自动提取问答对",
                        "timestamp": "2024-08-06 10:01:00",
                        "type": "text"
                    }
                ]
            }
            
            test_file_path = Path("test_upload.json")
            with open(test_file_path, 'w', encoding='utf-8') as f:
                json.dump(test_data, f, ensure_ascii=False, indent=2)
            
            # 上传测试文件
            with open(test_file_path, 'rb') as f:
                files = {'file': ('test_upload.json', f, 'application/json')}
                response = self.session.post(f"{self.api_base}/upload/file", files=files, timeout=30)
            
            # 清理测试文件
            if test_file_path.exists():
                test_file_path.unlink()
            
            if response.status_code == 200:
                data = response.json()
                upload_id = data.get('data', {}).get('upload_id')
                extracted = data.get('data', {}).get('total_extracted', 0)
                saved = data.get('data', {}).get('total_saved', 0)
                self.log_result("文件上传", True, f"上传ID: {upload_id}, 提取: {extracted}, 保存: {saved}")
                return upload_id
            else:
                self.log_result("文件上传", False, f"HTTP状态码: {response.status_code}")
                return None
        except Exception as e:
            self.log_result("文件上传", False, "上传失败", str(e))
            return None
    
    def run_all_tests(self):
        """运行所有测试"""
        print("🧪 开始API集成测试")
        print("="*50)
        
        # 基础API测试
        self.test_health_check()
        self.test_api_info()
        
        # 数据接口测试
        categories = self.test_categories()
        qa_pairs = self.test_qa_list()
        
        # 搜索功能测试
        self.test_search_basic()
        self.test_search_suggestions()
        
        # 上传功能测试
        upload_id = self.test_file_upload()
        self.test_upload_history()
        
        # 管理功能测试
        self.test_admin_stats()
        self.test_admin_health()
        
        # 测试结果汇总
        print("\n" + "="*50)
        print("📊 测试结果汇总")
        print("="*50)
        
        passed = sum(1 for r in self.test_results if r['success'])
        failed = len(self.test_results) - passed
        
        print(f"总测试数: {len(self.test_results)}")
        print(f"通过: {passed}")
        print(f"失败: {failed}")
        print(f"成功率: {passed/len(self.test_results)*100:.1f}%")
        
        if failed > 0:
            print(f"\n❌ 失败的测试:")
            for result in self.test_results:
                if not result['success']:
                    print(f"  - {result['test']}: {result['message']}")
        else:
            print("\n🎉 所有测试通过！")
        
        return failed == 0

def main():
    """主函数"""
    import argparse
    parser = argparse.ArgumentParser(description='API集成测试')
    parser.add_argument('--url', default='http://localhost:5000', help='服务器URL')
    args = parser.parse_args()
    
    tester = APITester(args.url)
    success = tester.run_all_tests()
    
    if not success:
        exit(1)

if __name__ == '__main__':
    main()