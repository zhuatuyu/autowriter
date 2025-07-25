#!/usr/bin/env python3
"""
API测试脚本
"""
import requests
import json

def test_api():
    base_url = "http://localhost:8000"
    
    # 测试健康检查
    try:
        response = requests.get(f"{base_url}/api/health")
        print(f"健康检查: {response.status_code}")
        print(f"响应: {response.json()}")
    except Exception as e:
        print(f"健康检查失败: {e}")
        return
    
    # 测试获取案例专家报告列表
    try:
        project_id = "project_1753431475113"
        response = requests.get(f"{base_url}/api/workspace/case-expert/{project_id}/reports")
        print(f"\n获取报告列表: {response.status_code}")
        if response.status_code == 200:
            reports = response.json()
            print(f"找到 {len(reports)} 个报告")
            for report in reports:
                print(f"  - {report['title']} ({report['id']})")
        else:
            print(f"错误: {response.text}")
    except Exception as e:
        print(f"获取报告列表失败: {e}")
    
    # 测试获取特定报告内容
    try:
        report_id = "case_report_搜索国内外关于'数字化城市管理'的成功案例，重点包括政府主导项目、技术应用模式、实施成效及可复制经验_20250725_162121.md"
        response = requests.get(f"{base_url}/api/workspace/case-expert/{project_id}/report/{report_id}")
        print(f"\n获取报告内容: {response.status_code}")
        if response.status_code == 200:
            report = response.json()
            print(f"报告标题: {report['title']}")
            print(f"内容长度: {len(report['content'])} 字符")
            print(f"修改时间: {report['modified']}")
        else:
            print(f"错误: {response.text}")
    except Exception as e:
        print(f"获取报告内容失败: {e}")

if __name__ == "__main__":
    test_api() 