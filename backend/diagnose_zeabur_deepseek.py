#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Zeabur部署环境DeepSeek问题诊断脚本
"""

import os
import sys
import json
import requests
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

def check_environment_variables():
    """检查环境变量配置"""
    print("=== 环境变量检查 ===")
    
    required_vars = [
        'DEEPSEEK_API_KEY',
        'DEEPSEEK_BASE_URL', 
        'DEEPSEEK_MODEL',
        'DEEPSEEK_TIMEOUT',
        'LLM_ENABLED'
    ]
    
    issues = []
    
    for var in required_vars:
        value = os.getenv(var)
        if var == 'DEEPSEEK_API_KEY':
            if not value:
                print(f"❌ {var}: 未设置")
                issues.append(f"{var}未设置")
            else:
                print(f"✅ {var}: {value[:10]}...{value[-4:]}")
        else:
            if not value:
                print(f"⚠️ {var}: 未设置 (将使用默认值)")
            else:
                print(f"✅ {var}: {value}")
    
    # 检查LLM_ENABLED的值
    llm_enabled = os.getenv('LLM_ENABLED', 'true').lower()
    if llm_enabled not in ['true', '1', 'yes', 'on']:
        print(f"❌ LLM_ENABLED: {llm_enabled} (LLM功能已禁用)")
        issues.append("LLM功能已禁用")
    
    return issues

def check_network_connectivity():
    """检查网络连接"""
    print("\n=== 网络连接检查 ===")
    
    base_url = os.getenv('DEEPSEEK_BASE_URL', 'https://api.deepseek.com')
    
    try:
        # 测试基础连接
        print(f"🔄 测试连接到 {base_url}...")
        response = requests.get(base_url, timeout=10)
        print(f"✅ 基础连接正常 (状态码: {response.status_code})")
        return True
    except requests.exceptions.Timeout:
        print("❌ 连接超时 - 可能是网络问题或防火墙阻止")
        return False
    except requests.exceptions.ConnectionError:
        print("❌ 连接错误 - 无法连接到DeepSeek服务器")
        return False
    except Exception as e:
        print(f"❌ 连接异常: {e}")
        return False

def test_api_call():
    """测试API调用"""
    print("\n=== API调用测试 ===")
    
    api_key = os.getenv('DEEPSEEK_API_KEY')
    base_url = os.getenv('DEEPSEEK_BASE_URL', 'https://api.deepseek.com')
    model = os.getenv('DEEPSEEK_MODEL', 'deepseek-reasoner')
    timeout = int(os.getenv('DEEPSEEK_TIMEOUT', '300'))
    
    if not api_key:
        print("❌ 无法测试API调用: API密钥未设置")
        return False
    
    url = f"{base_url}/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "你是一个测试助手。"},
            {"role": "user", "content": "请简单回复'测试成功'"}
        ],
        "temperature": 0.1,
        "max_tokens": 20,
    }
    
    try:
        print(f"🔄 调用API: {url}")
        response = requests.post(url, headers=headers, json=payload, timeout=timeout)
        
        print(f"HTTP状态码: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
            print(f"✅ API调用成功")
            print(f"模型回复: {content}")
            return True
        elif response.status_code == 401:
            print("❌ API密钥无效或已过期")
            return False
        elif response.status_code == 429:
            print("❌ API调用频率限制")
            return False
        else:
            print(f"❌ API调用失败")
            print(f"响应内容: {response.text}")
            return False
            
    except requests.exceptions.Timeout:
        print(f"❌ API调用超时 (>{timeout}s)")
        return False
    except Exception as e:
        print(f"❌ API调用异常: {e}")
        return False

def check_zeabur_specific_issues():
    """检查Zeabur特定问题"""
    print("\n=== Zeabur部署特定检查 ===")
    
    issues = []
    
    # 检查是否在容器环境中
    if os.path.exists('/.dockerenv'):
        print("✅ 检测到Docker容器环境")
    else:
        print("ℹ️ 未检测到Docker容器环境")
    
    # 检查端口配置
    port = os.getenv('PORT')
    if port:
        print(f"✅ PORT环境变量: {port}")
    else:
        print("⚠️ PORT环境变量未设置")
    
    # 检查.env文件是否存在
    if os.path.exists('.env'):
        print("✅ .env文件存在")
    else:
        print("⚠️ .env文件不存在 - Zeabur应该通过环境变量配置")
        issues.append(".env文件不存在")
    
    # 检查gunicorn配置
    print("ℹ️ 生产环境使用gunicorn启动")
    print("ℹ️ 确保Zeabur环境变量中已正确配置DEEPSEEK_API_KEY")
    
    return issues

def generate_solution_suggestions(env_issues, network_ok, api_ok, zeabur_issues):
    """生成解决方案建议"""
    print("\n=== 解决方案建议 ===")
    
    if env_issues:
        print("🔧 环境变量问题:")
        for issue in env_issues:
            if "DEEPSEEK_API_KEY" in issue:
                print("   - 在Zeabur控制台的环境变量中设置DEEPSEEK_API_KEY")
            elif "LLM功能已禁用" in issue:
                print("   - 在Zeabur控制台设置LLM_ENABLED=true")
    
    if not network_ok:
        print("🔧 网络连接问题:")
        print("   - 检查Zeabur服务器的网络连接")
        print("   - 确认DeepSeek API服务正常")
        print("   - 检查是否有防火墙或网络策略阻止外部API调用")
    
    if not api_ok and network_ok:
        print("🔧 API调用问题:")
        print("   - 验证DEEPSEEK_API_KEY是否正确")
        print("   - 检查API密钥是否有足够的配额")
        print("   - 确认API密钥未过期")
    
    if zeabur_issues:
        print("🔧 Zeabur部署问题:")
        for issue in zeabur_issues:
            if ".env文件不存在" in issue:
                print("   - 在Zeabur控制台配置所有必要的环境变量")
                print("   - 不要依赖.env文件，使用平台环境变量")
    
    print("\n📋 Zeabur环境变量配置清单:")
    print("   DEEPSEEK_API_KEY=你的API密钥")
    print("   DEEPSEEK_BASE_URL=https://api.deepseek.com")
    print("   DEEPSEEK_MODEL=deepseek-reasoner")
    print("   DEEPSEEK_TIMEOUT=300")
    print("   LLM_ENABLED=true")

def main():
    print("Zeabur部署环境DeepSeek问题诊断")
    print("=" * 50)
    
    # 检查环境变量
    env_issues = check_environment_variables()
    
    # 检查网络连接
    network_ok = check_network_connectivity()
    
    # 测试API调用
    api_ok = test_api_call() if network_ok else False
    
    # 检查Zeabur特定问题
    zeabur_issues = check_zeabur_specific_issues()
    
    # 生成解决方案
    generate_solution_suggestions(env_issues, network_ok, api_ok, zeabur_issues)
    
    # 总结
    print("\n=== 诊断总结 ===")
    if not env_issues and network_ok and api_ok:
        print("🎉 所有检查通过，DeepSeek功能应该正常工作")
    else:
        print("⚠️ 发现问题，请根据上述建议进行修复")
        if env_issues:
            print(f"   - 环境变量问题: {len(env_issues)}个")
        if not network_ok:
            print("   - 网络连接问题")
        if not api_ok:
            print("   - API调用问题")
        if zeabur_issues:
            print(f"   - Zeabur部署问题: {len(zeabur_issues)}个")

if __name__ == "__main__":
    main()