#学校验证方法
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote
import os
from typing import Dict, Optional
import json
from difyAPI import call_dify_api  # 导入difyAPI模块

class SchoolVerifier:
    def __init__(self):
        pass

    def search_google(self, school_name: str) -> Optional[str]:
        """进行Google搜索并返回第一个结果的URL"""
        print(f"开始搜索学校: {school_name}")
        try:
            search_url = f"https://www.google.com/search?q={quote(school_name)}+学校+官方网站"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            response = requests.get(search_url, headers=headers)
            print(f"Google搜索状态码: {response.status_code}")
            
            soup = BeautifulSoup(response.text, 'html.parser')
            first_result = soup.find('div', {'class': 'g'})
            if first_result:
                link = first_result.find('a')
                if link:
                    print(f"找到搜索结果URL: {link['href']}")
                    return link['href']
            print("未找到搜索结果")
            return None
        except Exception as e:
            print(f"Google搜索出错: {str(e)}")
            return None

    def get_website_content(self, url: str) -> Optional[str]:
        """获取网站内容"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'ja,en-US;q=0.7,en;q=0.3',
                'Accept-Encoding': 'gzip, deflate, br'
            }
            
            response = requests.get(url, headers=headers)
            
            # 尝试检测编码
            if response.encoding.upper() == 'ISO-8859-1':
                # 如果检测到的编码是 ISO-8859-1，尝试使用其他日语编码
                encodings = ['utf-8', 'shift_jis', 'euc-jp', 'iso-2022-jp']
                content = None
                
                for encoding in encodings:
                    try:
                        response.encoding = encoding
                        content = response.text
                        if not any(c == '' for c in content):
                            break
                    except UnicodeDecodeError:
                        continue
            else:
                # 使用网站声明的编码
                content = response.text

            if not content:
                print("无法正确解码网页内容")
                return None

            soup = BeautifulSoup(content, 'html.parser')
            
            # 提取包含元数据和标题的文本
            text_content = soup.title.string if soup.title else ""
            meta_description = soup.find('meta', {'name': 'description'})
            if meta_description:
                text_content += " " + meta_description.get('content', '')
            
            # 从正文中提取前1000个字符
            main_content = ' '.join(soup.stripped_strings)
            text_content += " " + main_content[:3000]
            
            print(f"获取到的网站内容: {text_content}")
            return text_content
        except Exception as e:
            print(f"获取网站内容出错: {str(e)}")
            return None

    #通过页面数据整理新闻信息
    def get_news_from_website(self, website_content: str) -> Dict:
        try:
            question = f"""
            用300字整理主要内容，如果有新闻，请列表显示，然后用日文输出。
            {website_content}
            """
            print("Dify APIで新闻信息整理中...")
            answer = call_dify_api(question)
            print(f"新闻信息: {answer}")
            return answer
        except Exception as e:
            print(f"获取新闻信息出错: {str(e)}")
            return None
    
    def verify_school(self, school_name: str, website_content: str) -> Dict:
        """Dify APIを使用して学校を検証する"""
        print(f"学校の検証を開始: {school_name}")
        try:
            question = f"""
            以下のウェブサイトの内容を分析し、このウェブサイトが「{school_name}」の公式サイトである可能性を判断してください。

            ウェブサイトの内容:
            {website_content}

            0から100までの数字で回答してください。数字は公式サイトである可能性を示すパーセンテージです。
            例：90
            """
            print("Dify APIで検証中...")
            
            answer = call_dify_api(question)
            print(f"検証結果: {answer}")
            
            try:
                confidence = int(''.join(filter(str.isdigit, answer)))
                confidence = min(100, max(0, confidence))
                
                if confidence >= 90:
                    reason = "公式サイトである可能性が非常に高いです"
                elif confidence >= 70:
                    reason = "公式サイトである可能性が高いです"
                elif confidence >= 50:
                    reason = "公式サイトである可能性があります"
                elif confidence >= 30:
                    reason = "公式サイトでない可能性があります"
                else:
                    reason = "公式サイトでない可能性が高いです"
                
                return {
                    "is_match": confidence >= 50,
                    "confidence": confidence,
                    "reason": reason
                }
            except:
                return {
                    "is_match": False,
                    "confidence": 0,
                    "reason": "判断できません"
                }
        except Exception as e:
            print(f"Dify APIエラー: {str(e)}")
            return {
                "is_match": False,
                "confidence": 0,
                "reason": "検証中にエラーが発生しました"
            }

    def verify(self, school_name: str) -> Dict:
        """検証プロセスを実行"""
        url = self.search_google(school_name)
        if not url:
            return {
                "url": None,
                "verification": "学校のウェブサイトが見つかりません",
                "details": "関連サイトが見つかりません"
            }

        content = self.get_website_content(url)
        if not content:
            return {
                "url": url,
                "verification": "ウェブサイトの内容を取得できません",
                "details": "ウェブサイトにアクセスできません"
            }

        #验证学校网站是否为官方网站 
        result = self.verify_school(school_name, content)
        return {
            "url": url,
            "verification": f"{result['confidence']}%",
            "details": result["reason"]
        }
