#!/usr/bin/env python3
"""
微信群聊数据格式转换工具
将 chatlog 导出的复杂JSON格式转换为知识库系统预期的简单格式
"""

import json
import sys
import re
from datetime import datetime
from typing import List, Dict, Any

def parse_timestamp(time_str: str) -> int:
    """将 ISO 时间字符串转换为时间戳"""
    try:
        dt = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
        return int(dt.timestamp() * 1000)
    except:
        return int(datetime.now().timestamp() * 1000)

def extract_content_from_chatlog_message(msg: Dict[str, Any]) -> str:
    """从 chatlog 消息中提取文本内容"""
    content = ""
    
    # 普通文本消息
    if msg.get('content') and isinstance(msg['content'], str):
        content = msg['content'].strip()
    
    # 复合消息内容
    if msg.get('contents'):
        contents = msg['contents']
        
        # 描述内容
        if contents.get('desc'):
            content = contents['desc'].strip()
        
        # 聊天记录内容
        if contents.get('recordInfo') and contents['recordInfo'].get('DataList'):
            data_list = contents['recordInfo']['DataList']
            if data_list.get('DataItems'):
                for item in data_list['DataItems']:
                    if item.get('DataDesc'):
                        # 处理嵌套的聊天记录
                        nested_content = item['DataDesc'].strip()
                        if nested_content and len(nested_content) > len(content):
                            content = nested_content
    
    # 清理内容
    if content:
        # 移除用户名前缀（如 "林: "）
        content = re.sub(r'^[^:：]+[:：]\s*', '', content)
        # 移除多余的空白字符
        content = re.sub(r'\s+', ' ', content).strip()
    
    return content

def convert_chatlog_to_simple_format(chatlog_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """将 chatlog 数据转换为简单格式"""
    converted_messages = []
    message_id = 1
    
    for msg in chatlog_data:
        # 跳过空消息或系统消息
        if msg.get('type') in [3, 10000] or not msg.get('senderName'):
            continue
        
        # 提取消息内容
        content = extract_content_from_chatlog_message(msg)
        
        # 跳过空内容或太短的消息
        if not content or len(content.strip()) < 10:
            continue
        
        # 跳过纯表情或特殊字符
        if re.match(r'^[\s\U0001F300-\U0001F9FF\u2600-\u27BF\u2B05-\u2B07\u2934-\u2935\u2B05-\u2B07\u25B6\u25C0\u23CF-\u23FA\U0001F680-\U0001F6FF]+$', content):
            continue
        
        # 处理时间戳
        timestamp = parse_timestamp(msg.get('time', ''))
        
        # 获取发送者名称
        sender_name = msg.get('senderName', '未知用户')
        
        # 创建简化消息
        simple_msg = {
            "id": f"msg_{message_id:06d}",
            "timestamp": timestamp,
            "from_user": sender_name,
            "content": content,
            "message_type": "text"
        }
        
        converted_messages.append(simple_msg)
        message_id += 1
    
    return converted_messages

def main():
    if len(sys.argv) != 3:
        print("使用方法: python convert_chatlog_data.py <输入文件> <输出文件>")
        print("示例: python convert_chatlog_data.py chatlog_export.json converted_data.json")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2]
    
    try:
        print(f"读取原始数据: {input_file}")
        with open(input_file, 'r', encoding='utf-8') as f:
            chatlog_data = json.load(f)
        
        print(f"原始消息数量: {len(chatlog_data)}")
        
        # 转换数据格式
        print("转换数据格式...")
        converted_data = convert_chatlog_to_simple_format(chatlog_data)
        
        print(f"转换后消息数量: {len(converted_data)}")
        
        # 保存转换后的数据
        print(f"保存转换后数据: {output_file}")
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(converted_data, f, ensure_ascii=False, indent=2)
        
        print("✅ 转换完成!")
        print(f"📊 统计信息:")
        print(f"   - 原始消息: {len(chatlog_data)} 条")
        print(f"   - 有效消息: {len(converted_data)} 条")
        print(f"   - 转换率: {len(converted_data)/len(chatlog_data)*100:.1f}%")
        
        # 显示一些样例
        if converted_data:
            print(f"\n📝 转换样例:")
            for i, msg in enumerate(converted_data[:3]):
                print(f"   {i+1}. [{msg['from_user']}]: {msg['content'][:50]}...")
    
    except FileNotFoundError:
        print(f"❌ 错误: 找不到输入文件 {input_file}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"❌ 错误: JSON 格式错误 - {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 错误: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()