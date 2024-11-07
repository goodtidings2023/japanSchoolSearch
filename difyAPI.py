# 导入必要的库
import requests
import json

def call_dify_api(question, stream=False):
    print("开始调用Dify API...")
    
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
        "response_mode": "streaming",  # 使用streaming模式
        "conversation_id": "",
        "user": "LukeLiu"
    }

    try:
        print("发送请求中...")
        response = requests.post(url, headers=headers, json=data, stream=True)
        
        if response.status_code != 200:
            print(f"API请求失败: {response.status_code}")
            print(f"错误信息: {response.text}")
            raise Exception("API请求失败，请稍后重试")

        if stream:
            # 流式输出模式
            for line in response.iter_lines():
                if line:
                    try:
                        line_text = line.decode('utf-8')
                        if line_text.startswith('data: '):
                            json_str = line_text[6:]  
                            if json_str.strip() == '[DONE]':
                                break
                            json_data = json.loads(json_str)
                            
                            if json_data.get('event') == 'message':
                                yield json_data.get('answer', '')
                            elif json_data.get('event') == 'error':
                                raise Exception(json_data.get('message', '未知错误'))
                                
                    except json.JSONDecodeError:
                        continue
        else:
            # 非流式输出模式
            full_response = ''
            for line in response.iter_lines():
                if line:
                    try:
                        line_text = line.decode('utf-8')
                        if line_text.startswith('data: '):
                            json_str = line_text[6:]
                            if json_str.strip() == '[DONE]':
                                break
                            json_data = json.loads(json_str)
                            
                            if json_data.get('event') == 'message':
                                full_response += json_data.get('answer', '')
                            elif json_data.get('event') == 'error':
                                raise Exception(json_data.get('message', '未知错误'))
                                
                    except json.JSONDecodeError:
                        continue
            return full_response

    except Exception as e:
        print(f"调用API时发生错误: {str(e)}")
        raise e

