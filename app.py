from flask import Flask, render_template, request, jsonify
import requests
from bs4 import BeautifulSoup
import urllib.parse
import math
import re
from difyAPI import call_dify_api
import json
import logging
from school_verify import SchoolVerifier
import os

app = Flask(__name__)

def build_search_url(params, page=1):
    base_url = "https://www.minkou.jp/primary/search"
    
    # 构建URL路径
    url_parts = []
    
    # 添加排序方式
    if params.get('sort') == 'rating':
        url_parts.append('v=3')
    
    # 添加都道府县
    if params.get('prefecture'):
        url_parts.append(params['prefecture'])
    
    # 添加市区町村代码
    if params.get('city'):
        url_parts.append(params['city'])
    
    # 构建查询参数
    query_parts = []
    
    # 添加学校类型 (c=1表示私立, c=2表示国立, c=3表示公立)
    if params.get('category'):
        query_parts.append(f"c={params['category']}")
    
    # 添加性别类型 (g=1表示共学, g=2表示男校, g=3表示女校)
    if params.get('gender'):
        query_parts.append(f"g={params['gender']}")
    
    # 添加关键词搜索
    if params.get('keyword'):
        # URL编码关键词
        encoded_keyword = urllib.parse.quote(params['keyword'])
        query_parts.append(f"k={encoded_keyword}")
    
    # 添加分页参数
    if page > 1:
        query_parts.append(f"page={page}")
    
    # 组合URL
    url = base_url
    if url_parts:
        url += "/" + "/".join(url_parts)
    if query_parts:
        url += "/" + "/".join(query_parts)
    
    # 确保URL以斜杠结尾
    if not url.endswith('/'):
        url += '/'
        
    return url

def get_pagination_info(soup):
    try:
        pagination_div = soup.find('div', class_='sch-search-sortpager-txt')
        if pagination_div:
            text = pagination_div.get_text(strip=True)
            # 解析类似 "1049件中 21-40件を表示" 的文本
            total_count = int(text.split('件中')[0])
            current_range = text.split('件中')[1].split('件を表示')[0].strip()
            start, end = map(int, current_range.split('-'))
            
            return {
                'total_count': total_count,
                'current_page_start': start,
                'current_page_end': end,
                'total_pages': math.ceil(total_count / 20)  # 每页20条数据
            }
    except Exception as e:
        print(f"解析分页信息错误: {str(e)}")
    
    return None

def scrape_schools(params=None, page=1):
    if not params:
        return {'schools': [], 'pagination': None}
    
    url = build_search_url(params, page)
    print(f"构建的URL: {url}")
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ja,en-US;q=0.7,en;q=0.3',
            'Referer': 'https://www.minkou.jp/primary/',
            'Connection': 'keep-alive',
        }
        
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 获取分页信息
        pagination = get_pagination_info(soup)
        
        # 找到包所有学校的容器
        search_list = soup.find('div', class_='sch-search-list')
        if not search_list:
            return {'schools': [], 'pagination': pagination}
            
        school_list = search_list.find_all('div', class_='sch-searchBox')
        schools = []

        for school in school_list:
            try:
                # 获取学校链接
                link_tag = school.find('a')
                school_link = f"https://www.minkou.jp{link_tag['href']}" if link_tag and 'href' in link_tag.attrs else ''
                school_id = link_tag['href'].split('/')[-2] if link_tag and 'href' in link_tag.attrs else ''
                school_link = f"school/{school_id}"
                # 获取学校信息容器
                info_box = school.find('div', class_='sch-searchBox-info')
                if not info_box:
                    continue

                # 获取学校名称
                name_box = info_box.find('div', class_='sch-searchBox-name')
                name = name_box.find('h3').text.strip() if name_box and name_box.find('h3') else 'N/A'

                # 获取学校类型和性别类型
                icon_box = name_box.find('div', class_='sch-searchBox-icon') if name_box else None
                icon_lists = icon_box.find_all('ul') if icon_box else []
                
                school_type = icon_lists[0].find('li').text.strip() if len(icon_lists) > 0 and icon_lists[0].find('li') else 'N/A'
                gender_type = icon_lists[1].find('li').text.strip() if len(icon_lists) > 1 and icon_lists[1].find('li') else 'N/A'

                # 获取地址
                address = name_box.find('span').text.strip() if name_box and name_box.find('span') else 'N/A'

                # 获取评分信息
                review_box = info_box.find('div', class_='sch-searchBox-review')
                if review_box:
                    rating = review_box.find('div', class_='review-txt-pointTotal')
                    rating = rating.text.strip() if rating else 'N/A'
                    
                    review_count = review_box.find('div', class_='review-txt-countReview')
                    review_count = review_count.find('span').text.strip() if review_count and review_count.find('span') else '0'
                else:
                    rating = 'N/A'
                    review_count = '0'

                schools_data = {
                    'name': name,
                    'school_type': school_type,
                    'gender': gender_type,
                    'address': address,
                    'rating': rating,
                    'review_count': review_count,
                    'link': school_link,
                    'school_id': school_id
                }

                schools.append(schools_data)
            except Exception as e:
                print(f"解析学校数据错误: {str(e)}")
                continue

        return {
            'schools': schools,
            'pagination': pagination
        }

    except Exception as e:
        print(f"爬取错误: {str(e)}")
        return {'schools': [], 'pagination': None}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/search', methods=['POST'])
def search():
    search_params = {
        'prefecture': request.form.get('prefecture'),
        'city': request.form.get('city'),
        'category': request.form.get('category'),
        'gender': request.form.get('gender'),
        'keyword': request.form.get('keyword'),
        'sort': request.form.get('sort')
    }
    
    page = int(request.form.get('page', 1))
    search_params = {k: v for k, v in search_params.items() if v}
    
    results = scrape_schools(search_params, page)
    print('搜索参数:', search_params)
    print('页码:', page)
    print('搜索结果:', results)
    return jsonify(results)

@app.route('/school/<school_id>')
def school_detail(school_id):
    # 构建URL
    url = f'https://www.minkou.jp/primary/school/{school_id}/'
    url_review = f'https://www.minkou.jp/primary/school/review/{school_id}/'
    
    try:
        # 获取页面内容
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

        # 获取学校信息
        response = requests.get(url, headers=headers)
        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.text, 'html.parser')

        # 获取口碑信息
        response_review = requests.get(url_review, headers=headers)
        response_review.encoding = 'utf-8'
        soup_review = BeautifulSoup(response_review.text, 'html.parser')
        
        # 提取学校信息
        school_data = {
            'school_name': '',
            'furigana': '',
            'address': '',
            'nearest_station': '',
            'phone': '',
            'uniform': '',
            'lunch': '',
            'events': '',
            'fees': ''
        }
        
        # 查找基本信息表格
        info_table = soup.find('table', class_='table-binfo')
        
        if info_table:
            rows = info_table.find_all('tr')
            for row in rows:
                th = row.find('th')
                td = row.find('td')
                if th and td:
                    key = th.text.strip()
                    value = td.text.strip()
                    
                    # 根据表头匹配相应字段
                    if '学校名' in key:
                        school_data['school_name'] = value
                    elif 'ふりがな' in key:
                        school_data['furigana'] = value
                    elif '所在地' in key:
                        # 提取地址文本，去除地图相关内容
                        address_p = td.find('p', class_='tx-address')
                        if address_p:
                            address_parts = []
                            for span in address_p.find_all('span'):
                                address_parts.append(span.text.strip())
                            school_data['address'] = ''.join(address_parts)
                    elif '最寄駅' in key:
                        school_data['nearest_station'] = value
                    elif '電話番号' in key:
                        school_data['phone'] = value
                    elif '制服' in key:
                        school_data['uniform'] = value
                    elif '給食' in key:
                        school_data['lunch'] = value
                    elif '行事' in key:
                        school_data['events'] = value
                    elif '学費' in key:
                        school_data['fees'] = value
        
        # 获取地图坐标（如果需要）
        map_div = soup.find('div', class_='js-schoolMap-open')
        if map_div:
            try:
                lat = map_div.get('data-lat', '')
                lon = map_div.get('data-lon', '')
                if lat and lon:
                    school_data['map_coords'] = {
                        'lat': lat,
                        'lon': lon
                    }
            except Exception as e:
                print(f"Error getting map coordinates: {str(e)}")
                school_data['map_coords'] = None
        
        # 获取口碑信息
        reviews = []
        review_list = soup_review.find('div', class_='mod-reviewList')
        if review_list:
            for review in review_list.find_all('li', id=lambda x: x and x.startswith('answer_')):
                review_data = {
                    'id': review.get('id', '').replace('answer_', ''),
                    'user_type': '',
                    'entry_year': '',
                    'title': '',
                    'post_date': '',
                    'rating': '',
                    'ratings_detail': {},
                    'overall_review': '',
                    'details': {},
                    'school_info': {},
                    'enrollment_info': {},
                    'helpful_count': ''
                }
                
                # 获取用户信息和基本数据
                top_info = review.find('div', class_='mod-reviewTop-inner')
                if top_info:
                    user_info = top_info.find('dd').get_text(strip=True).split('/')
                    review_data['user_type'] = user_info[0].strip()
                    review_data['entry_year'] = user_info[1].strip()
                    
                    title = top_info.find('div', class_='mod-reviewTitle')
                    review_data['title'] = title.text.strip() if title else ''
                    
                    date = top_info.find('div', class_='mod-reviewDate')
                    review_data['post_date'] = date.text.strip() if date else ''
                    
                    rating = top_info.find('span', class_='mod-reviewScore-num')
                    review_data['rating'] = rating.text.strip() if rating else ''

                # 获取详细评分
                ratings = review.find('div', class_='mod-reviewItem')
                if ratings:
                    ratings_text = ratings.text.strip('[]').split('｜')
                    for rating in ratings_text:
                        key, value = rating.strip().split(' ', 1)
                        review_data['ratings_detail'][key] = value.strip()

                # 获取详细评价
                review_content = review.find('div', class_='js-review-detail')
                if review_content:
                    # 获取总体评价
                    overall = review_content.find('div', text='総合評価')
                    if overall:
                        review_data['overall_review'] = overall.find_next('div', class_='mod-reviewList-txt').text.strip()
                    
                    # 获取各项详细评价
                    for item in review_content.find_all('div', class_='mod-reviewTitle3'):
                        key = item.text.strip()
                        value = item.find_next('div', class_='mod-reviewList-txt')
                        if value:
                            review_data['details'][key] = value.text.strip()

                    # 获取学校信息
                    school_info = review_content.find('div', text='小学校について')
                    if school_info:
                        for item in school_info.find_next('ul').find_all('li'):
                            key = item.find('div', class_='mod-reviewTitle3').text.strip()
                            value = item.find('div', class_='mod-reviewList-txt')
                            if value:
                                review_data['school_info'][key] = value.text.strip()

                    # 获取入学信息
                    enrollment = review_content.find('div', text='入学について')
                    if enrollment:
                        for item in enrollment.find_next('ul').find_all('li'):
                            key = item.find('div', class_='mod-reviewTitle3').text.strip()
                            value = item.find('div', class_='mod-reviewList-txt')
                            if value:
                                review_data['enrollment_info'][key] = value.text.strip()

                # 获取有用数量
                helpful = review.find('p', class_=lambda x: x and x.startswith('mod-voiceMini-sns-voted'))
                if helpful:
                    review_data['helpful_count'] = helpful.text.strip()

                reviews.append(review_data)

        # 将口碑数据添加到school_data中
        school_data['reviews'] = reviews
        return render_template('school_detail.html', **school_data)
        
    except Exception as e:
        print(f"Error fetching school details: {str(e)}")
        return f"Error: {str(e)}", 500

# 学校查找与验证
@app.route('/verify', methods=['GET', 'POST'])
def verify_school():
    result = None
    if request.method == 'POST':
        school_name = request.form.get('school_name')
        if school_name:
            verifier = SchoolVerifier()  # 确保不传递参数
            result = verifier.verify(school_name)
    
    return render_template('school_verify.html', result=result)

if __name__ == '__main__':
    app.run(debug=True)
