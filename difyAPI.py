# 导入必要的库
import requests
import json

def call_dify_api(question):
    print("正在调用 Dify API...")
    
    # 设置API的URL
    url = 'https://api.dify.ai/v1/chat-messages'

    # 设置API密钥
    api_key = "app-MByzCHn0QSrm40PXljtO6RLc"

    # 设置请求头
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json',
    }

    # 设置请求数据
    data = {
        "inputs": {},
        "query": question,
        "conversation_id": "",
        "user": "LukeLiu"
    }

    try:
        # 发送POST请求
        response = requests.post(url, headers=headers, json=data)
        
        if response.status_code == 200:
            response_data = response.json()
            # 直接返回answer内容
            return response_data.get('answer', '无法获取回答内容')
        else:
            return "API请求失败"
            
    except Exception as e:
        return f"发生错误: {str(e)}"
