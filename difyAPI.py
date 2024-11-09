# 导入必要的库
import requests
import json

def call_dify_api(question):
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
        "inputs": {},                # 输入参数，此处为空
        "query": question,           # 查询内容
        "response_mode": "stream", # 响应模式设置为流式
        "user": "LukeLiu"            # 用户标识
    }

    print("发送请求中...")
    # 发送POST请求
    with requests.post(url, headers=headers, data=json.dumps(data), stream=True) as response:
        print("请求已发送，开始接收流式响应...")
        
        for line in response.iter_lines():
            if line:
                try:
                    # 移除 'data: ' 前缀并解析JSON
                    json_str = line.decode('utf-8').replace('data: ', '')
                    json_data = json.loads(json_str)
                    if json_data['event'] == 'message':
                        answer = json_data.get('answer', '')
                        yield json.dumps({"answer": answer})  # 修正json.dumps参数

                except json.JSONDecodeError:
                    print(f"无法解析JSON: {line}")
                except KeyError:
                    print(f"JSON格式不符合预期: {json_data}")

    print("调用结束。")
