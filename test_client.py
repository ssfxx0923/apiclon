"""
测试客户端
用于测试AI API中继服务
"""
import requests
import json
import sys


def test_health():
    """测试健康检查端点"""
    print("=== 测试健康检查 ===")
    try:
        response = requests.get("http://localhost:8000/health")
        print(f"状态码: {response.status_code}")
        print(f"响应: {response.json()}")
        print()
        return response.status_code == 200
    except Exception as e:
        print(f"错误: {e}")
        return False


def test_service_info():
    """测试服务信息端点"""
    print("=== 测试服务信息 ===")
    try:
        response = requests.get("http://localhost:8000/")
        print(f"状态码: {response.status_code}")
        print(f"响应: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
        print()
        return response.status_code == 200
    except Exception as e:
        print(f"错误: {e}")
        return False


def test_list_models(api_key=None):
    """测试获取模型列表端点"""
    print("=== 测试获取模型列表 ===")
    
    headers = {}
    
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    
    try:
        response = requests.get(
            "http://localhost:8000/v1/models",
            headers=headers,
            timeout=30
        )
        print(f"状态码: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"响应: {json.dumps(data, indent=2, ensure_ascii=False)}")
            
            # 如果有模型列表，显示模型数量
            if "data" in data:
                print(f"可用模型数量: {len(data['data'])}")
                if data['data']:
                    print("模型列表:")
                    for model in data['data'][:5]:  # 只显示前5个模型
                        model_id = model.get('id', 'unknown')
                        print(f"  - {model_id}")
                    if len(data['data']) > 5:
                        print(f"  ... 还有 {len(data['data']) - 5} 个模型")
        else:
            print(f"响应: {response.text}")
        
        print()
        return response.status_code == 200
    except Exception as e:
        print(f"错误: {e}")
        return False


def test_chat_completion(api_key=None):
    """测试聊天完成端点（非流式）"""
    print("=== 测试聊天完成（非流式）===")
    
    headers = {
        "Content-Type": "application/json"
    }
    
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    
    data = {
        "model": "glm-4.5",
        "messages": [
            {"role": "user", "content": "你好，请说'测试成功'"}
        ],
        "stream": False
    }
    
    try:
        response = requests.post(
            "http://localhost:8000/v1/chat/completions",
            json=data,
            headers=headers,
            timeout=30
        )
        print(f"状态码: {response.status_code}")
        print(f"响应: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
        print()
        return response.status_code == 200
    except Exception as e:
        print(f"错误: {e}")
        return False


def test_chat_completion_stream(api_key=None):
    """测试聊天完成端点（流式）"""
    print("=== 测试聊天完成（流式）===")
    
    headers = {
        "Content-Type": "application/json"
    }
    
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    
    data = {
        "model": "glm-4.5",
        "messages": [
            {"role": "user", "content": "你好"}
        ],
        "stream": True
    }
    
    try:
        response = requests.post(
            "http://localhost:8000/v1/chat/completions",
            json=data,
            headers=headers,
            stream=True,
            timeout=30
        )
        print(f"状态码: {response.status_code}")
        print("流式响应内容:")
        
        for chunk in response.iter_content(chunk_size=None):
            if chunk:
                print(chunk.decode('utf-8'), end='', flush=True)
        
        print("\n")
        return response.status_code == 200
    except Exception as e:
        print(f"错误: {e}")
        return False


def main():
    """主函数"""
    print("=" * 50)
    print("AI API中继服务 - 测试客户端")
    print("=" * 50)
    print()
    
    # 可选：从命令行参数获取API密钥
    api_key = None
    if len(sys.argv) > 1:
        api_key = sys.argv[1]
        print(f"使用API密钥: {api_key[:10]}...")
        print()
    
    results = []
    
    # 运行测试
    results.append(("健康检查", test_health()))
    results.append(("服务信息", test_service_info()))
    results.append(("获取模型列表", test_list_models(api_key)))
    results.append(("聊天完成（非流式）", test_chat_completion(api_key)))
    results.append(("聊天完成（流式）", test_chat_completion_stream(api_key)))
    
    # 打印测试结果
    print("=" * 50)
    print("测试结果总结")
    print("=" * 50)
    for test_name, result in results:
        status = "✓ 通过" if result else "✗ 失败"
        print(f"{test_name}: {status}")
    
    # 统计
    passed = sum(1 for _, result in results if result)
    total = len(results)
    print()
    print(f"总计: {passed}/{total} 通过")
    
    # 返回退出码
    return 0 if passed == total else 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)

