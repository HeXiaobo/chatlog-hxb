#!/usr/bin/env python3

import re

def test_question_patterns():
    """测试问题识别模式"""
    
    # 真实的问题文本
    question_text = "胡老师，今年秋季孩子学校的学费账单已下发，但是 fafsa 给的金额到现在还没出，学校说是推迟了。CSS从去年开始就没有申请下来费用，问过学校，原因是有银行存款，您有好的办法吗？"
    
    print(f"测试文本: {question_text[:50]}...")
    
    # 测试各种模式
    patterns = {
        '问号检测': r'.*[?？].*',
        '请教模式': r'.*[您你].*(有|什么|怎么).*(好的)?.*[办法方法建议].*[吗？?]?',
        '老师咨询': r'.*老师.*[，,].*',
        '求助模式': r'.*(老师|请教|咨询|求助|帮忙).*',
        '教育术语': r'.*(FAFSA|CSS|学费|助学金|申请|学校|孩子).*',
    }
    
    for name, pattern in patterns.items():
        match = re.search(pattern, question_text, re.IGNORECASE)
        result = "✅ 匹配" if match else "❌ 不匹配"
        print(f"{name:10}: {result}")
        if match:
            print(f"           匹配内容: {match.group()[:50]}...")
    
    # 计算问题得分
    question_score = 0
    
    # 基础长度
    if len(question_text) > 5:
        question_score += 0.5
        print(f"长度加分: +0.5 (总分: {question_score})")
    
    # 疑问词检测
    question_words = ['什么', '如何', '怎么', '为什么', '哪里', '哪个', '能否', '可以', '请问', '有没有', '您有', '老师']
    for word in question_words:
        if word in question_text:
            question_score += 0.5
            print(f"疑问词 '{word}': +0.5 (总分: {question_score})")
            break
    
    # 教育词汇
    educational_words = ['FAFSA', 'CSS', '学费', '助学金', '申请', '学校', '孩子', '办法', '建议']
    for word in educational_words:
        if word in question_text:
            question_score += 0.3
            print(f"教育词汇 '{word}': +0.3 (总分: {question_score})")
            break
    
    # 请教模式
    if re.search(r'.*[您你].*(有|什么|怎么).*(好的)?.*[办法方法建议].*[吗？?]?', question_text):
        question_score += 0.8
        print(f"请教模式: +0.8 (总分: {question_score})")
    
    # 求助模式
    if re.search(r'.*(老师|请教|咨询|求助|帮忙).*', question_text):
        question_score += 0.4
        print(f"求助模式: +0.4 (总分: {question_score})")
    
    is_question = question_score >= 0.3
    print(f"\n最终得分: {question_score}")
    print(f"是否为问题: {'✅ 是' if is_question else '❌ 否'} (阈值: 0.3)")
    
    return is_question

if __name__ == "__main__":
    test_question_patterns()