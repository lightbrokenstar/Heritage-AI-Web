import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import requests
import base64
import os
import json
import uuid  
from datetime import datetime
from streamlit_echarts import st_echarts, Map
from openai import OpenAI  

# 1. 网页全局配置
st.set_page_config(page_title="华夏遗珍 | 数智交互平台", layout="wide", initial_sidebar_state="collapsed")

# ================= 核心跳转拦截器 (跨页面通信) =================
if "nav" in st.query_params:
    target_nav = st.query_params["nav"]
    target_site = st.query_params.get("site", None)
    if target_nav == "baike":
        st.session_state.current_page = "遗珍百科"
        st.session_state.detail_item = target_site
    st.query_params.clear() 

# ================= 路由与状态管理 =================
if 'current_page' not in st.session_state:
    st.session_state.current_page = "首页视界"
if 'detail_item' not in st.session_state:
    st.session_state.detail_item = None
if 'view_post_id' not in st.session_state:
    st.session_state.view_post_id = None

# 用于记录用户的百科浏览历史
if 'search_history' not in st.session_state:
    st.session_state.search_history = []

# ================= 本地图片转 Base64 引擎 =================
@st.cache_data
def get_image_base64(img_path, fallback_url):
    try:
        if os.path.exists(img_path):
            with open(img_path, "rb") as img_file:
                return "data:image/jpeg;base64," + base64.b64encode(img_file.read()).decode('utf-8')
    except Exception:
        pass
    return fallback_url

img1 = get_image_base64("image/The_Great_Wall_of_China.jpg", "https://images.unsplash.com/photo-1508804185872-d7badad00f7d?w=1200&q=80")
img2 = get_image_base64("image/gugong.jpg", "https://images.unsplash.com/photo-1584646098378-0874589d79b1?w=1200&q=80")
img3 = get_image_base64("image/West_Lake.jpg", "https://images.unsplash.com/photo-1626014903706-5b4372e90f62?w=1200&q=80")
img4 = get_image_base64("image/TerracotaArmy.jpg", "https://images.unsplash.com/photo-1597953600326-9fba8e1a1293?w=1200&q=80")
img5 = get_image_base64("image/Lasa.jpg", "https://images.unsplash.com/photo-1583208754160-7ea00f1c305a?w=1200&q=80") 
# 🔥 新增敦煌莫高窟本地图片解析
img6 = get_image_base64("image/dunhuang.jpg", "https://images.unsplash.com/photo-1543013313-094191be8606?w=1200&q=80") 

# ================= 维基百科 API 实时接口 =================
@st.cache_data(ttl=86400) 
def fetch_wikipedia_data(title):
    # API 增加了 prop=pageimages 来抓取词条原图
    url = f"https://zh.wikipedia.org/w/api.php?action=query&prop=extracts|pageimages&piprop=original&explaintext&titles={title}&redirects=1&format=json&utf8=1&variant=zh-cn"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    result = {"text": "", "image": None}
    for attempt in range(3):
        try:
            res = requests.get(url, headers=headers, timeout=12).json()
            pages = res.get("query", {}).get("pages", {})
            for pid, pdata in pages.items():
                if pid != '-1':
                    result["text"] = pdata.get('extract', '')
                    if 'original' in pdata:
                        result["image"] = pdata['original'].get('source', None)
                    return result
            break
        except Exception:
            continue
    return result

# 核心数据库
rich_encyclopedia = {
    "长城": {"img": img1, "year": "1987年首批入选", "intro": "长城是古代中国为抵御塞北游牧部落联盟侵袭而修筑的规模浩大的军事工程，跨越千年的防御工程奇迹。"},
    "明清皇家宫殿": {"img": img2, "year": "1987年首批入选", "intro": "明清两代的皇家宫殿，旧称紫禁城，位于北京中轴线的中心，是中国古代宫廷建筑之精华。"},
    "西湖": {"img": img3, "year": "2011年入选", "intro": "将秀丽的自然风光与深厚的文化底蕴完美融合，是中国江南水乡与东方审美精神的杰出代表。"},
    "秦始皇陵及兵马俑坑": {"img": img4, "year": "1987年首批入选", "intro": "秦始皇陵的陪葬坑，出土的数以千计的兵马俑被誉为“世界第八大奇迹”。"},
    "拉萨布达拉宫历史建筑群": {"img": img5, "year": "1994年入选", "intro": "世界上海拔最高、集宫殿、城堡和寺院于一体的宏伟建筑，是藏传佛教的圣地。"}
}

# ================= 小红书式社区数据引擎 =================
COMMENTS_FILE = "posts.json"

def load_posts():
    if os.path.exists(COMMENTS_FILE):
        try:
            with open(COMMENTS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if data and "title" not in data[0]:
                    raise ValueError("Old data format")
                return data
        except Exception:
            pass
    
    # 固定演示数据的 ID，防止刷新丢失状态
    default_posts = [
        {
            "id": "demo_post_1",
            "title": "烟雨下江南，西湖绝美打卡点！",
            "name": "江南烟雨", 
            "avatar": "🍵", 
            "time": "2024-05-21 14:15", 
            "content": "刚跟着 AI 导游做了一份去杭州西湖的攻略，风景真的太美了！雷峰夕照绝绝子，强烈建议大家一定要去坐一下摇橹船！给大家分享一张我的打卡照片！", 
            "image": img3,
            "likes": 128,
            "comments": [
                {"c_id": "demo_comment_1", "name": "历史发烧友", "avatar": "🐉", "content": "求一份详细的游览路线！", "time": "2024-05-21 15:20", "up": 12, "down": 0}
            ]
        },
        {
            "id": "demo_post_2",
            "title": "不到长城非好汉，震撼！",
            "name": "历史发烧友", 
            "avatar": "🐉", 
            "time": "2024-05-20 10:30", 
            "content": "这个网站做得太棒了！排版和资料都极其专业，长城的百科介绍让我大开眼界！实地去爬长城真的是一种心灵的震撼。", 
            "image": img1,
            "likes": 56,
            "comments": []
        }
    ]
    # 自动保存一次固定数据，解决闪退 bug
    with open(COMMENTS_FILE, "w", encoding="utf-8") as f:
        json.dump(default_posts, f, ensure_ascii=False, indent=4)
    return default_posts

def save_posts(posts):
    with open(COMMENTS_FILE, "w", encoding="utf-8") as f:
        json.dump(posts, f, ensure_ascii=False, indent=4)
# 2. 深度美化 CSS 
st.markdown("""
    <style>
    header[data-testid="stHeader"] {display: none !important;}
    [data-testid="collapsedControl"] {display: none !important;}
    [data-testid="stSidebar"] {display: none !important;}
    .block-container { padding-top: 0rem !important; padding-bottom: 1rem !important; max-width: 95% !important; margin-top: 0rem !important;}
    
    div.stButton > button {
        width: 100%; border: none; background-color: transparent; color: #5C1D16; 
        font-size: 1.25rem; font-weight: normal; border-bottom: 3px solid transparent; border-radius: 0; padding: 12px 0;
    }
    div.stButton > button:hover { border-bottom: 3px solid #8B3E04; color: #8B3E04; background-color: #FDF8F5;}
    
    .main-title {font-size: 2.6rem; font-weight: 900; color: #5C1D16; margin-bottom: 0.5rem; letter-spacing: 2px;}
    .sub-title {font-size: 1.3rem; color: #8C6A4F; margin-bottom: 1.5rem; border-bottom: 2px solid #EAD8C3; padding-bottom: 10px;}
    
    .metric-card {background-color: #FAFAFA; padding: 10px 20px; border-radius: 8px; border-left: 5px solid #8B3E04; box-shadow: 0px 4px 10px rgba(0,0,0,0.05);}
    .metric-card h2 {color: #8B3E04; margin-top: 0; margin-bottom: 2px; font-size: 2.0rem; font-weight: bold;}
    .metric-card p {color: #555555; margin-bottom: 0; font-size: 1.0rem; font-weight: 500;}
    
    .detail-header {text-align: center; margin-bottom: 20px;}
    .detail-title {font-size: 2.5rem; color: #5C1D16; font-weight: 900;}
    .detail-tag {display: inline-block; background-color: #FDF8F5; color: #8B3E04; padding: 5px 15px; border-radius: 20px; font-size: 1rem; font-weight: 600; margin: 5px; border: 1px solid #EAD8C3;}
    .section-title {color: #8B3E04; font-size: 1.5rem; font-weight: bold; margin-top: 25px; border-left: 4px solid #C68244; padding-left: 10px; background-color: #FDF8F5; padding-top: 5px; padding-bottom: 5px;}
    .detail-text {font-size: 1.15rem; color: #444; line-height: 1.8; text-align: justify; margin-top: 10px;}
    
    .custom-table { width: 100%; border-collapse: collapse; font-size: 1.15rem; text-align: center; margin-bottom: 20px;}
    .custom-table th { background-color: #5C1D16; color: white; padding: 12px; text-align: center; font-weight: 600;}
    .custom-table td { padding: 12px; border-bottom: 1px solid #EAD8C3; color: #333;}
    .custom-table tr:hover { background-color: #FDF8F5; }
    
    .list-category {color: #A0522D; font-size: 1.4rem; margin-top: 20px; margin-bottom: 10px; font-weight: bold; border-bottom: 1px solid #EAD8C3; padding-bottom: 5px;}
    .map-link {font-size: 1.15rem; color: #333333; line-height: 2.0; margin-left: 10px; text-decoration: none; display: block; transition: all 0.2s;}
    .map-link:hover {color: #8B3E04; font-weight: bold; padding-left: 5px;}
    .map-link::before {content: "• "; color: #C68244;}
    
    /* 社区帖子网格与详情 CSS */
    .community-header {color: #5C1D16; font-size: 1.5rem; font-weight: 900; margin-top: 0px; margin-bottom: 15px; border-bottom: 2px solid #EAD8C3; padding-bottom: 8px;}
    .post-card {background-color: #FAFAFA; border-radius: 12px; border: 1px solid #EEEEEE; overflow: hidden; margin-bottom: 15px; box-shadow: 0 2px 5px rgba(0,0,0,0.05); transition: transform 0.2s;}
    .post-card:hover {transform: translateY(-3px); box-shadow: 0 5px 15px rgba(0,0,0,0.1);}
    .post-cover {width: 100%; height: 180px; object-fit: cover; background-color: #EAD8C3; display: flex; align-items: center; justify-content: center; color: #8B3E04; font-size: 2rem;}
    .post-info {padding: 12px;}
    .post-title {font-weight: 900; color: #333; font-size: 1.1rem; margin-bottom: 8px; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;}
    .post-meta {display: flex; align-items: center; justify-content: space-between; font-size: 0.9rem; color: #777;}
    .post-author {display: flex; align-items: center; gap: 5px;}
    
    .detail-post-box {background-color: #FAFAFA; border-radius: 12px; padding: 25px; box-shadow: 0 4px 10px rgba(0,0,0,0.05);}
    .detail-author-row {display: flex; align-items: center; gap: 15px; margin-bottom: 20px;}
    .detail-avatar {font-size: 2.2rem; background-color: #FDF8F5; border-radius: 50%; width: 60px; height: 60px; display: flex; align-items: center; justify-content: center; border: 2px solid #EAD8C3;}
    .detail-content {font-size: 1.15rem; color: #333; line-height: 1.8; margin-bottom: 20px; text-align: justify;}
    .detail-img {max-width: 100%; border-radius: 8px; margin-top: 15px; margin-bottom: 20px; box-shadow: 0 4px 15px rgba(0,0,0,0.1);}
    
    .comment-list-box {margin-top: 30px; border-top: 1px solid #EAD8C3; padding-top: 20px;}
    .sub-comment {display: flex; gap: 12px; margin-bottom: 15px; padding-bottom: 15px; border-bottom: 1px dashed #EEEEEE;}
    .sub-avatar {font-size: 1.5rem; width: 40px; height: 40px; background-color: #EEEEEE; border-radius: 50%; display: flex; align-items: center; justify-content: center;}
    .sub-body {flex: 1;}
    .sub-name {font-weight: bold; color: #555; font-size: 0.95rem; margin-bottom: 5px;}
    .sub-text {color: #333; font-size: 1.05rem; margin-bottom: 8px;}
    .sub-actions {display: flex; gap: 15px; font-size: 0.85rem; color: #888;}
    </style>
""", unsafe_allow_html=True)

# 3. 核心数据库 A：地图分布专用
heritage_data = {
    "北京市": {"文化": ["长城", "明清皇家宫殿", "周口店遗址", "颐和园", "天坛", "明清皇家陵寝", "北京中轴线", "大运河"], "自然": [], "双重": []},
    "天津市": {"文化": ["大运河"], "自然": [], "双重": []},
    "河北省": {"文化": ["长城", "承德避暑山庄及其周围寺庙", "明清皇家陵寝", "大运河"], "自然": ["中国黄（渤）海候鸟栖息地"], "双重": []},
    "山西省": {"文化": ["平遥古城", "云冈石窟", "五台山"], "自然": [], "双重": []},
    "内蒙古自治区": {"文化": ["元上都"], "自然": ["巴丹吉林沙漠"], "双重": []},
    "辽宁省": {"文化": ["明清皇家宫殿", "明清皇家陵寝", "高句丽王城、王陵及贵族墓葬"], "自然": ["中国黄（渤）海候鸟栖息地"], "双重": []},
    "吉林省": {"文化": ["高句丽王城、王陵及贵族墓葬"], "自然": [], "双重": []},
    "上海市": {"文化": [], "自然": ["中国黄（渤）海候鸟栖息地"], "双重": []},
    "江苏省": {"文化": ["苏州古典园林", "明清皇家陵寝", "大运河"], "自然": ["中国黄（渤）海候鸟栖息地"], "双重": []},
    "浙江省": {"文化": ["西湖", "良渚遗址", "大运河"], "自然": ["中国丹霞"], "双重": []},
    "安徽省": {"文化": ["皖南古村落—西递、宏村", "大运河"], "自然": [], "双重": ["黄山"]},
    "福建省": {"文化": ["福建土楼", "鼓浪屿", "泉州：宋元中国的世界海洋商贸中心"], "自然": ["中国丹霞"], "双重": ["武夷山 (世界遗产)"]},
    "江西省": {"文化": ["庐山"], "自然": ["三清山", "中国丹霞"], "双重": ["武夷山 (世界遗产)"]},
    "山东省": {"文化": ["曲阜孔庙、孔林和孔府", "大运河"], "自然": ["中国黄（渤）海候鸟栖息地"], "双重": ["泰山"]},
    "河南省": {"文化": ["龙门石窟", "殷墟", "登封“天地之中”历史建筑群", "大运河", "丝绸之路：长安—天山廊道的路网"], "自然": [], "双重": []},
    "湖北省": {"文化": ["武当山古建筑群", "明清皇家陵寝", "土司遗址"], "自然": ["湖北神农架国家公园"], "双重": []},
    "湖南省": {"文化": ["土司遗址"], "自然": ["武陵源风景名胜区", "中国丹霞"], "双重": []},
    "广东省": {"文化": ["开平碉楼"], "自然": ["中国丹霞"], "双重": []},
    "广西壮族自治区": {"文化": ["花山岩画"], "自然": ["中国南方喀斯特"], "双重": []},
    "重庆市": {"文化": ["大足石刻"], "自然": ["中国南方喀斯特", "湖北神农架国家公园"], "双重": []},
    "四川省": {"文化": ["都江堰"], "自然": ["九寨沟", "黄龙风景名胜区", "四川大熊猫栖息地"], "双重": ["乐山大佛"]},
    "贵州省": {"文化": ["土司遗址"], "自然": ["梵净山", "中国南方喀斯特", "中国丹霞"], "双重": []},
    "云南省": {"文化": ["丽江古城", "红河哈尼梯田", "普洱景迈山古茶林"], "自然": ["云南三江并流保护区", "澄江化石地", "中国南方喀斯特"], "双重": []},
    "西藏自治区": {"文化": ["拉萨布达拉宫历史建筑群"], "自然": [], "双重": []},
    "陕西省": {"文化": ["秦始皇陵及兵马俑", "丝绸之路：长安—天山廊道的路网"], "自然": [], "双重": []},
    "甘肃省": {"文化": ["长城", "莫高窟", "丝绸之路：长安—天山廊道的路网"], "自然": [], "双重": []},
    "青海省": {"文化": [], "自然": ["可可西里"], "双重": []},
    "宁夏回族自治区": {"文化": ["西夏陵"], "自然": [], "双重": []},
    "新疆维吾尔自治区": {"文化": ["丝绸之路：长安—天山廊道的路网"], "自然": ["天山山脉"], "双重": []},
    "澳门特别行政区": {"文化": ["澳门历史城区"], "自然": [], "双重": []}
}

# 提取用于百科检索的扁平化列表
all_heritage_list = []
seen_names = set()
for prov, categories in heritage_data.items():
    for cat_name, items in categories.items():
        for item_name in items:
            if item_name not in seen_names:
                cat_full = "世界文化遗产" if cat_name == "文化" else "世界自然遗产" if cat_name == "自然" else "文化与自然双重遗产"
                all_heritage_list.append({"name": item_name, "province": prov, "category": cat_full})
                seen_names.add(item_name)

# 核心数据库
rich_encyclopedia = {
    "长城": {"img": img1, "year": "1987年首批入选", "intro": "长城是古代中国为抵御塞北游牧部落联盟侵袭而修筑的规模浩大的军事工程，跨越千年的防御工程奇迹。"},
    "明清皇家宫殿": {"img": img2, "year": "1987年首批入选", "intro": "明清两代的皇家宫殿，旧称紫禁城，位于北京中轴线的中心，是中国古代宫廷建筑之精华。"},
    "西湖": {"img": img3, "year": "2011年入选", "intro": "将秀丽的自然风光与深厚的文化底蕴完美融合，是中国江南水乡与东方审美精神的杰出代表。"},
    "秦始皇陵及兵马俑": {"img": img4, "year": "1987年首批入选", "intro": "秦始皇陵的陪葬坑，出土的数以千计的兵马俑被誉为“世界第八大奇迹”。"},
    "拉萨布达拉宫历史建筑群": {"img": img5, "year": "1994年入选", "intro": "世界上海拔最高、集宫殿、城堡和寺院于一体的宏伟建筑，是藏传佛教的圣地。"}
}

# ================= 智能降级渲染引擎 =================
def generate_robust_encyclopedia(site_name, base_info):
    if site_name in rich_encyclopedia:
        return rich_encyclopedia[site_name]
    
    wiki_text = fetch_wikipedia_data(site_name)
    if wiki_text:
        return {
            "img": None,
            "intro": wiki_text[:350] + ("..." if len(wiki_text)>350 else ""),
            "history": "依据历史文献记载，该遗产经历了深远的岁月洗礼，" + (wiki_text[350:700] + "..." if len(wiki_text)>350 else "其历史底蕴成为中华文明或自然演变的生动见证。"),
            "features": f"该遗产作为{base_info['category']}，在选址、形态或生态系统上展现了独特的地域风貌与突出的普遍价值。",
            "status": "目前已被列入国家重点保护计划，通过建立完善的监测机制，确保这一世界级瑰宝能够世代传承。"
        }
    
    return {
        "img": None,
        "intro": f"{site_name}是位于中国{base_info['province']}的一项重要的{base_info['category']}。它不仅是中华民族宝贵的财富，也为全人类的文明与生态多样性作出了杰出贡献。该遗产凭借其独特的普遍价值，被联合国教科文组织正式列入《世界遗产名录》。",
        "history": f"作为{base_info['category']}的杰出代表，{site_name}承载了深厚的历史积淀与鲜明的地域特色。历经岁月的洗礼，它完整地保留了其真实性与完整性，成为见证中国悠久历史与自然演变的生动化石。",
        "features": f"该遗产项目集中展现了{base_info['province']}地区独特的文化风貌与自然景观。其在建筑格局、生态形态及文化内涵上，均体现出极高的审美价值与科学研究价值。",
        "status": f"目前，{site_name}已建立起严格的保护与监测机制。国家与地方政府通过数字化建档、生态修复与预防性保护等多种手段，致力于确保这一世界瑰宝能够世代传承。"
    }

# ================= 路由与状态管理 =================
if 'current_page' not in st.session_state:
    st.session_state.current_page = "首页视界"
if 'detail_item' not in st.session_state:
    st.session_state.detail_item = None
if 'view_post_id' not in st.session_state:
    st.session_state.view_post_id = None

# 定义极度可靠的回调函数，解决点击没反应的问题
def set_view_post(pid):
    st.session_state.view_post_id = pid

def clear_view_post():
    st.session_state.view_post_id = None

# ================= 顶部全局导航栏 =================
st.markdown('''
    <div style="background-color: #5C1D16; padding: 18px 25px; color: #FFFFFF; font-size: 1.55rem; font-weight: bold; margin-bottom: 5px; text-align: left; letter-spacing: 3px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
        华夏遗珍 | 中国世界遗产数智交互平台
    </div>
''', unsafe_allow_html=True)

col1, col2, col3, col4, col5 = st.columns(5)
with col1: 
    if st.button("首页视界", use_container_width=True): st.session_state.current_page = "首页视界"; st.session_state.detail_item = None
with col2: 
    if st.button("数据大屏", use_container_width=True): st.session_state.current_page = "数据大屏"; st.session_state.detail_item = None
with col3: 
    if st.button("遗珍百科", use_container_width=True): st.session_state.current_page = "遗珍百科"; st.session_state.detail_item = None
with col4: 
    if st.button("AI 智游", use_container_width=True): st.session_state.current_page = "AI 智游"; st.session_state.detail_item = None
with col5: 
    if st.button("寻迹社区", use_container_width=True): st.session_state.current_page = "寻迹社区"; st.session_state.detail_item = None; clear_view_post()

st.write("") 

# ================= 页面一：首页 =================
if st.session_state.current_page == "首页视界":
    st.markdown('<h3 class="sub-title" style="margin-top:0;">让千年文化遗产在数字时代焕发新生，触摸历史的温度。</h3>', unsafe_allow_html=True)

    html_template = """
    <!DOCTYPE html>
    <html>
    <head>
    <style>
        body { margin: 0; padding: 0; font-family: sans-serif; }
        .hero-container { position: relative; width: 100%; height: 600px; border-radius: 12px; overflow: hidden; box-shadow: 0 10px 30px rgba(0,0,0,0.2); }
        .bg-image { width: 100%; height: 100%; object-fit: cover; transition: opacity 0.6s ease-in-out; opacity: 1; }
        .overlay { position: absolute; top: 0; left: 0; width: 100%; height: 100%; background: linear-gradient(to right, rgba(92,29,22,0.85) 0%, rgba(92,29,22,0.4) 50%, rgba(0,0,0,0) 100%); }
        .thumbnails { position: absolute; left: 30px; top: 50%; transform: translateY(-50%); display: flex; flex-direction: column; gap: 12px; z-index: 10; }
        .thumb-wrapper { position: relative; width: 65px; height: 65px; border-radius: 50%; cursor: pointer; border: 3px solid rgba(255,255,255,0.5); overflow: hidden; transition: all 0.3s ease; box-shadow: 0 4px 10px rgba(0,0,0,0.5); }
        .thumb-wrapper:hover, .thumb-wrapper.active { border-color: #E6B885; transform: scale(1.15); }
        .thumb-wrapper img { width: 100%; height: 100%; object-fit: cover; }
        
        .text-content { position: absolute; left: 140px; bottom: 50px; z-index: 10; width: 700px; display: flex; justify-content: space-between; align-items: flex-end; }
        .text-info { max-width: 500px; }
        .text-info h1 { font-size: 3rem; margin: 0 0 10px 0; color: #E6B885; text-shadow: 2px 2px 4px rgba(0,0,0,0.8); }
        .text-info p { font-size: 1.15rem; margin: 0; line-height: 1.6; text-shadow: 1px 1px 3px rgba(0,0,0,0.8); color: #EEEEEE; }
        
        .btn-square { display: inline-block; padding: 10px 20px; border: 2px solid #FFFFFF; background-color: transparent; color: #FFFFFF; text-decoration: none; font-size: 1.1rem; font-weight: bold; cursor: pointer; transition: all 0.3s; margin-bottom: 5px; border-radius: 4px; letter-spacing: 2px;}
        .btn-square:hover { background-color: #FFFFFF; color: #5C1D16; }
    </style>
    </head>
    <body>
    <div class="hero-container">
        <img id="main-bg" class="bg-image" src="IMG_SRC_1">
        <div class="overlay"></div>
        <div class="thumbnails">
            <div class="thumb-wrapper active" onclick="changeSlide(0, this, true)"><img src="IMG_SRC_1"></div>
            <div class="thumb-wrapper" onclick="changeSlide(1, this, true)"><img src="IMG_SRC_2"></div>
            <div class="thumb-wrapper" onclick="changeSlide(2, this, true)"><img src="IMG_SRC_3"></div>
            <div class="thumb-wrapper" onclick="changeSlide(3, this, true)"><img src="IMG_SRC_4"></div>
            <div class="thumb-wrapper" onclick="changeSlide(4, this, true)"><img src="IMG_SRC_5"></div>
        </div>
        <div class="text-content">
            <div class="text-info">
                <h1 id="main-title">长城</h1>
                <p id="main-desc">世界文化遗产，中华民族的精神象征与智慧结晶，跨越千年的防御工程奇迹。</p>
            </div>
            <a id="jump-btn" href="#" target="_top" class="btn-square">查看更多</a>
        </div>
    </div>
    <script>
        const slides = [
            { img: 'IMG_SRC_1', title: '长城', desc: '世界文化遗产，中华民族的精神象征与智慧结晶，跨越千年的防御工程奇迹。' },
            { img: 'IMG_SRC_2', title: '明清皇家宫殿', desc: '世界文化遗产，明清两代皇家宫殿，中国古代宫廷建筑之精华，无与伦比的历史杰作。' },
            { img: 'IMG_SRC_3', title: '西湖', desc: '世界文化景观遗产，秀丽的自然风光与深厚的文化底蕴完美融合，江南水乡的代表。' },
            { img: 'IMG_SRC_4', title: '拉萨布达拉宫历史建筑群', desc: '世界文化遗产，世界上海拔最高、集宫殿、城堡和寺院于一体的宏伟建筑。' },
            { img: 'IMG_SRC_5', title: '秦始皇陵及兵马俑', desc: '世界文化遗产，被誉为“世界第八大奇迹”，展现了秦代高超的雕塑艺术与大一统气象。' }
        ];
        
        //务必替换成你的最新公网网址，注意末尾带斜杠 /
        let safeBaseUrl = "https://heritage-ai-web-zb7cjxs74jjewtu45itj4d.streamlit.app/"; 
        if (window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1") {
            safeBaseUrl = "http://localhost:8501/";
        }
        
        function getTargetUrl(title) {
            return safeBaseUrl + "?nav=baike&site=" + encodeURIComponent(title);
        }
        
        document.getElementById('jump-btn').href = getTargetUrl(slides[0].title);
        
        // 加入自动轮播逻辑
        let currentIndex = 0;
        let playTimer = setInterval(autoPlay, 4500); // 每4.5秒自动切换
        
        function autoPlay() {
            let nextIndex = (currentIndex + 1) % slides.length;
            let thumbs = document.querySelectorAll('.thumb-wrapper');
            changeSlide(nextIndex, thumbs[nextIndex], false);
        }
        
        function changeSlide(index, element, isManual) {
            if (isManual) { // 如果用户手动点击，重置计时器，防止画面乱跳
                clearInterval(playTimer);
                playTimer = setInterval(autoPlay, 4500);
            }
            currentIndex = index;
            const bg = document.getElementById('main-bg');
            const title = document.getElementById('main-title');
            const desc = document.getElementById('main-desc');
            const jumpBtn = document.getElementById('jump-btn');
            
            document.querySelectorAll('.thumb-wrapper').forEach(el => el.classList.remove('active'));
            element.classList.add('active');
            
            bg.style.opacity = 0;
            setTimeout(() => { 
                bg.src = slides[index].img; 
                title.innerText = slides[index].title; 
                desc.innerText = slides[index].desc; 
                jumpBtn.href = getTargetUrl(slides[index].title);
                bg.style.opacity = 1; 
            }, 400); 
        }
    </script>
    </body>
    </html>
    """
    final_html = html_template.replace("IMG_SRC_1", img1).replace("IMG_SRC_2", img2).replace("IMG_SRC_3", img3).replace("IMG_SRC_4", img5).replace("IMG_SRC_5", img4)
    components.html(final_html, height=620)

    # 1. 航拍视界
    st.markdown('<div class="section-title" style="margin-top: 40px; margin-bottom: 20px; font-size: 1.8rem;">航拍视界</div>', unsafe_allow_html=True)
    video_col1, video_col2 = st.columns([2, 1])
    with video_col1:
        if os.path.exists("heritage.mp4"):
            st.video("heritage.mp4", format="video/mp4", autoplay=True, muted=True, loop=True)
        else:
            st.error("演示提示：未检测到本地视频。请下载一段无版权的高清航拍风景视频，命名为 heritage.mp4 并放在代码所在的同一文件夹内。")
            
    with video_col2:
        st.markdown('''
            <div style="background:#FAFAFA; border:1px solid #EAD8C3; padding:25px; border-radius:12px; height:100%; display:flex; flex-direction:column; justify-content:center; box-shadow: 0 4px 15px rgba(0,0,0,0.03);">
                <h2 style="color:#5C1D16; margin-top:0; font-weight:900;">飞越中华，一眼千年</h2>
                <div style="width: 50px; height: 4px; background-color: #C68244; margin-bottom: 15px;"></div>
                <p style="color:#555; font-size:1.1rem; line-height:1.8; text-align:justify;">
                    漫步在故宫的红墙黄瓦之间，欣赏建筑的魅力。<br><br>
                    <b>数字影像技术</b>正在打破物理空间的限制，让那些沉淀在岁月长河中的文化瑰宝，以前所未有的宏大视角展现在我们面前。
                </p>
            </div>
        ''', unsafe_allow_html=True)

    #  2. VR云游
    st.markdown('<div class="section-title" style="margin-top: 40px; margin-bottom: 10px; font-size: 1.8rem;">VR云游</div>', unsafe_allow_html=True)
    
    vr_options = {
        "紫禁城 (明清皇家宫殿)": {"img": img2, "title": "紫禁城全景沉浸式云游", "desc": "开启元宇宙视界，漫步太和殿广场", "link": "https://pano.dpm.org.cn/"},
        "敦煌莫高窟": {"img": img6, "title": "数字敦煌 高清壁画全景", "desc": "毫米级数字微距，探索千年佛教艺术", "link": "https://www.e-dunhuang.com/"},
        "秦始皇陵及兵马俑坑": {"img": img4, "title": "大秦兵马俑", "desc": "身临其境，检阅两千年前的地下军阵", "link": "https://baike.baidu.com/museum/qinshihuang"}
    }
    
    c1, c2 = st.columns([1, 4])
    with c1: st.markdown("<div style='margin-top: 5px; font-weight: bold; color: #5C1D16; font-size:1.1rem;'>切换云游场景：</div>", unsafe_allow_html=True)
    with c2: selected_vr_key = st.selectbox("VR 场景选项", list(vr_options.keys()), label_visibility="collapsed")
    
    vr_data = vr_options[selected_vr_key]
    
    # 注入悬停特效 CSS
    st.markdown("""
        <style>
        .vr-btn { background-color: #C68244; color: #FFFFFF !important; padding: 15px 40px; border-radius: 50px; text-decoration: none; font-size: 1.25rem; font-weight: bold; transition: all 0.3s; box-shadow: 0 4px 15px rgba(0,0,0,0.3); border: 2px solid #EAD8C3; display: inline-block;}
        .vr-btn:hover { transform: scale(1.05); background-color: #FFFFFF; color: #C68244 !important; border-color: #C68244; box-shadow: 0 6px 20px rgba(198,130,68,0.5);}
        </style>
    """, unsafe_allow_html=True)
    
    # 构建动态切换底层图库的高级传送门
    st.markdown(f'''
        <div style="position: relative; width: 100%; height: 450px; border-radius: 12px; overflow: hidden; box-shadow: 0 10px 30px rgba(0,0,0,0.15); border: 1px solid #EAD8C3; background-image: url('{vr_data["img"]}'); background-size: cover; background-position: center; transition: background-image 0.5s;">
            <div style="position: absolute; top: 0; left: 0; width: 100%; height: 100%; background: rgba(92,29,22,0.65); display: flex; flex-direction: column; align-items: center; justify-content: center;">
                <div style="font-size: 4.5rem; margin-bottom: 15px; color: white; text-shadow: 0 4px 15px rgba(0,0,0,0.3);">🥽</div>
                <h2 style="color: white; font-weight: 900; font-size: 2.2rem; letter-spacing: 3px; text-shadow: 2px 2px 8px rgba(0,0,0,0.6); margin-bottom: 10px; text-align: center;">{vr_data["title"]}</h2>
                <p style="color: #FDF8F5; font-size: 1.15rem; margin-bottom: 35px; text-shadow: 1px 1px 4px rgba(0,0,0,0.5);">{vr_data["desc"]}</p>
                <a href="{vr_data["link"]}" target="_blank" class="vr-btn">
                    点击开启全屏VR体验
                </a>
            </div>
        </div>
    ''', unsafe_allow_html=True)

# ================= 页面二：大屏  =================
elif st.session_state.current_page == "数据大屏":
    import re  #  引入正则引擎来智能提取年份
    
    # 建立权威的年份与遗产映射字典
    heritage_by_year = {
        "1987": ["长城", "明清皇家宫殿", "秦始皇陵及兵马俑坑", "莫高窟", "周口店遗址", "泰山"],
        "1990": ["黄山"], "1992": ["九寨沟", "黄龙风景名胜区", "武陵源风景名胜区"],
        "1994": ["承德避暑山庄及其周围寺庙", "曲阜孔庙、孔林和孔府", "武当山古建筑群", "拉萨布达拉宫历史建筑群"],
        "1996": ["庐山", "峨眉山—乐山大佛"], "1997": ["平遥古城", "苏州古典园林", "丽江古城"],
        "1998": ["颐和园", "天坛"], "1999": ["大足石刻", "武夷山 (世界遗产)"],
        "2000": ["皖南古村落—西递、宏村", "明清皇家陵寝", "龙门石窟", "青城山—都江堰"],
        "2001": ["云冈石窟"], "2003": ["云南三江并流保护区"], "2004": ["高句丽王城、王陵及贵族墓葬"],
        "2005": ["澳门历史城区"], "2006": ["殷墟", "四川大熊猫栖息地"],
        "2007": ["开平碉楼", "中国南方喀斯特"], "2008": ["福建土楼", "三清山"],
        "2009": ["五台山"], "2010": ["登封“天地之中”历史建筑群", "中国丹霞"],
        "2011": ["西湖"], "2012": ["澄江化石地", "元上都"], "2013": ["新疆天山", "红河哈尼梯田"],
        "2014": ["大运河", "丝绸之路：长安—天山廊道的路网"], "2015": ["土司遗址"],
        "2016": ["花山岩画", "湖北神农架国家公园"], "2017": ["可可西里", "鼓浪屿"],
        "2018": ["梵净山"], "2019": ["良渚遗址", "中国黄（渤）海候鸟栖息地"],
        "2021": ["泉州：宋元中国的世界海洋商贸中心"], "2023": ["普洱景迈山古茶林"],
        "2024": ["北京中轴线", "巴丹吉林沙漠"]
    }

    st.markdown('<h1 class="main-title">中国世界遗产数据库</h1>', unsafe_allow_html=True)
    st.markdown('<h3 class="sub-title">宏观数据统计、省级名录动态查询与保护指标评估</h3>', unsafe_allow_html=True)

    col1, col2, col3, col4 = st.columns(4)
    with col1: st.markdown('<div class="metric-card"><h2>60 项</h2><p>中国世界遗产总数</p></div>', unsafe_allow_html=True)
    with col2: st.markdown('<div class="metric-card"><h2>41 项</h2><p>世界文化遗产</p></div>', unsafe_allow_html=True)
    with col3: st.markdown('<div class="metric-card"><h2>15 项</h2><p>世界自然遗产</p></div>', unsafe_allow_html=True)
    with col4: st.markdown('<div class="metric-card"><h2>4 项</h2><p>文化与自然双重遗产</p></div>', unsafe_allow_html=True)

    st.write("---")

    # 时间轴点击数据穿透
    chart_col1, chart_col2 = st.columns([1.5, 1])
    with chart_col1:
        line_options = {
            "title": {"text": "中国历年新增世界遗产数量趋势 (点击节点查阅明细)", "left": "center", "textStyle": {"color": "#5C1D16", "fontSize": 16}},
            "tooltip": {"trigger": "axis"},
            "xAxis": {"type": "category", "data": ["1987", "1990", "1994", "1997", "2000", "2004", "2008", "2012", "2016", "2020", "2024"], "boundaryGap": False},
            "yAxis": {"type": "value"},
            "series": [{"data": [6, 1, 4, 3, 4, 3, 2, 2, 2, 1, 2], "type": "line", "smooth": True, 
                       "itemStyle": {"color": "#8B3E04"}, "areaStyle": {"color": "rgba(198, 130, 68, 0.3)"}, "label": {"show": True, "position": "top"}}]
        }
        # 捕捉点击的年份
        year_clicked = st_echarts(line_options, events={"click": "function(params) { return params.name; }"}, height="350px", key="timeline")

    with chart_col2:
        # 利用正则智能剥离异常字符，并将 HTML 整体合并渲染
        actual_year = None
        if year_clicked:
            match = re.search(r'(\d{4})', str(year_clicked))
            if match:
                actual_year = match.group(1)

        # 整体包裹 HTML
        box_html = '<div style="background:#FAFAFA; border:1px solid #EAD8C3; border-radius:8px; padding:20px; height:350px; overflow-y:auto; box-shadow:inset 0 2px 5px rgba(0,0,0,0.02);">'
        
        if actual_year:
            box_html += f'<h3 style="color:#5C1D16; margin-top:0;">{actual_year}年 入选档案</h3>'
            sites = heritage_by_year.get(actual_year, [])
            if sites:
                for s in sites:
                    box_html += f'<a href="?nav=baike&site={s}" target="_self" class="map-link">{s}</a>'
            else:
                box_html += '<p style="color:#888;">该年份暂无或未收录数据。</p>'
        else:
            box_html += '''
                <div style="display:flex; flex-direction:column; align-items:center; justify-content:center; height:100%; color:#888; padding-top:50px;">
                    <span style="font-size:2.5rem; margin-bottom:10px;">👈</span>
                    <span style="text-align:center;">点击左侧时间轴的数据节点<br>探索当年的申遗档案</span>
                </div>
            '''
        box_html += '</div>'
        
        # 一次性输出，解决空盒子Bug
        st.markdown(box_html, unsafe_allow_html=True)

    st.write("---")

    # 左边雷达图，右边加入南丁格尔玫瑰图
    chart_col3, chart_col4 = st.columns([1, 1.2])
    with chart_col3:
        radar_options = {
            "title": {"text": "综合保护指数评估雷达图", "left": "center", "textStyle": {"color": "#5C1D16", "fontSize": 16}},
            "tooltip": {},
            "radar": {"indicator": [{"name": "历史原真性", "max": 100}, {"name": "保护完好度", "max": 100}, {"name": "数字化普及", "max": 100}, {"name": "文化传播力", "max": 100}, {"name": "生态融合度", "max": 100}], "radius": "60%", "center": ["50%", "55%"]},
            "series": [{"name": "综合评估", "type": "radar", "data": [{"value": [95, 88, 75, 92, 85], "name": "全国平均水平"}], "itemStyle": {"color": "#C68244"}, "areaStyle": {"color": "rgba(198, 130, 68, 0.4)"}}]
        }
        st_echarts(radar_options, height="350px")
        
    with chart_col4:
        rose_options = {
            "title": {"text": "全国大区遗产分布格局", "left": "center", "textStyle": {"color": "#5C1D16", "fontSize": 16}},
            "tooltip": {"trigger": "item", "formatter": "{b} : {c}项 ({d}%)"},
            "color": ["#5C1D16", "#8B3E04", "#C68244", "#E6BA89", "#D9A05B", "#A0522D", "#CD853F"],
            "series": [
                {
                    "name": "大区分布",
                    "type": "pie",
                    "radius": [30, 120],
                    "center": ["50%", "55%"],
                    "roseType": "area",
                    "itemStyle": {"borderRadius": 5},
                    "label": {"show": True, "formatter": "{b}\n{c}项"},
                    "data": [
                        {"value": 14, "name": "华东地区"},
                        {"value": 12, "name": "西南地区"},
                        {"value": 11, "name": "华北地区"},
                        {"value": 9, "name": "西北地区"},
                        {"value": 7, "name": "华中地区"},
                        {"value": 5, "name": "华南地区"},
                        {"value": 2, "name": "东北地区"}
                    ]
                }
            ]
        }
        st_echarts(rose_options, height="350px")

    st.write("---")

    # 3. 交互地图区
    @st.cache_data
    def load_china_map():
        url = "https://geo.datav.aliyun.com/areas_v3/bound/100000_full.json"
        return requests.get(url).json()

    map_obj = Map("china", load_china_map())
    map_col, list_col = st.columns([1.2, 1])
    all_provinces = ["北京市", "天津市", "河北省", "山西省", "内蒙古自治区", "辽宁省", "吉林省", "黑龙江省", "上海市", "江苏省", "浙江省", "安徽省", "福建省", "江西省", "山东省", "河南省", "湖北省", "湖南省", "广东省", "广西壮族自治区", "海南省", "重庆市", "四川省", "贵州省", "云南省", "西藏自治区", "陕西省", "甘肃省", "青海省", "宁夏回族自治区", "新疆维吾尔自治区", "台湾省", "香港特别行政区", "澳门特别行政区"]

    with map_col:
        st.markdown('<h3 style="color:#5C1D16;">交互地图分布矩阵</h3>', unsafe_allow_html=True)
        map_data = []
        for prov in all_provinces:
            if prov in heritage_data:
                items = heritage_data[prov]
                total = len(items["文化"]) + len(items["自然"]) + len(items["双重"])
                map_data.append({"name": prov, "value": total})
            else:
                map_data.append({"name": prov, "value": 0})
                
        map_options = {
            "tooltip": {"trigger": "item", "formatter": "{b}<br/>遗产总数: {c} 项"},
            "visualMap": { "min": 0, "max": 8, "text": ["多", "少"], "realtime": False, "calculable": True, "inRange": {"color": ["#FDF8F5", "#E6BA89", "#C17942", "#8B3E04"]}, "textStyle": {"color": "#666666"} },
            "series": [{ "name": "遗产数量", "type": "map", "mapType": "china", "roam": True, "zoom": 1.3, "label": {"show": False}, "itemStyle": {"areaColor": "#FDF8F5", "borderColor": "#CCCCCC"}, "emphasis": {"label": {"show": True, "color": "#FFF", "fontWeight": "bold"}, "itemStyle": {"areaColor": "#5C2600"}}, "data": map_data }]
        }
        clicked_data = st_echarts(map_options, map=map_obj, events={"click": "function(params) { return params.name; }"}, height="600px", key="china_map")

    with list_col:
        st.markdown('<h3 style="color:#5C1D16;">地方遗珍名录查询</h3>', unsafe_allow_html=True)
        province_name = None
        if clicked_data:
            clicked_str = str(clicked_data)
            for prov in all_provinces:
                if prov in clicked_str:
                    province_name = prov
                    break
            
        if not province_name:
            st.info("请在左侧地图点击高亮的省份，查阅具体的遗产名录。")
        elif province_name not in heritage_data or (len(heritage_data[province_name]["文化"]) + len(heritage_data[province_name]["自然"]) + len(heritage_data[province_name]["双重"]) == 0):
            st.markdown(f'<h3 class="province-title">{province_name}</h3>', unsafe_allow_html=True)
            st.info("该省份暂未列入世界遗产名录，期待未来的发现与传承！")
        else:
            st.markdown(f'<h3 class="province-title">{province_name}</h3>', unsafe_allow_html=True)
            data = heritage_data[province_name]
            
            if data["文化"]:
                st.markdown('<div class="list-category">世界文化遗产</div>', unsafe_allow_html=True)
                for item in data["文化"]: st.markdown(f'<a href="?nav=baike&site={item}" target="_self" class="map-link">{item}</a>', unsafe_allow_html=True)
            if data["自然"]:
                st.markdown('<div class="list-category">世界自然遗产</div>', unsafe_allow_html=True)
                for item in data["自然"]: st.markdown(f'<a href="?nav=baike&site={item}" target="_self" class="map-link">{item}</a>', unsafe_allow_html=True)
            if data["双重"]:
                st.markdown('<div class="list-category">世界文化与自然双重遗产</div>', unsafe_allow_html=True)
                for item in data["双重"]: st.markdown(f'<a href="?nav=baike&site={item}" target="_self" class="map-link">{item}</a>', unsafe_allow_html=True)
                
# ================= 页面三：百科 =================
elif st.session_state.current_page == "遗珍百科":
    
    def get_exact_wiki_title(site_name):
        mapping = {
            "周口店北京人遗址": "周口店遗址",
            "北京及沈阳的明清皇家宫殿 (北京故宫)": "北京及沈阳的明清皇家宫殿",
            "明清皇家宫殿": "北京及沈阳的明清皇家宫殿",
            "杭州西湖文化景观": "西湖",
            "秦始皇陵及兵马俑": "秦始皇陵及兵马俑",
            "拉萨布达拉宫历史建筑群": "拉萨布达拉宫历史建筑群",
            "承德避暑山庄及其周围寺庙": "承德避暑山庄及其周围寺庙",
            "曲阜孔庙、孔林和孔府": "曲阜孔庙、孔林和孔府",
            "武当山古建筑群": "武当山古建筑群",
            "丽江古城": "丽江古城",
            "平遥古城": "平遥古城",
            "苏州古典园林": "苏州古典园林",
            "大足石刻": "大足石刻",
            "明清皇家陵寝": "明清皇家陵寝",
            "龙门石窟": "龙门石窟",
            "云冈石窟": "云冈石窟",
            "高句丽王城、王陵及贵族墓葬": "高句丽王城、王陵及贵族墓葬",
            "澳门历史城区": "澳门历史城区",
            "殷墟": "殷墟",
            "开平碉楼与村落": "开平碉楼",
            "福建土楼": "福建土楼",
            "登封“天地之中”历史建筑群": "登封“天地之中”历史建筑群",
            "元上都遗址": "元上都",
            "红河哈尼梯田文化景观": "红河哈尼梯田",
            "丝绸之路：长安-天山廊道的路网": "丝绸之路：长安—天山廊道的路网",
            "土司遗址": "土司遗址",
            "左江花山岩画文化景观": "花山岩画",
            "鼓浪屿：历史国际社区": "鼓浪屿",
            "良渚古城遗址": "良渚遗址",
            "泉州：宋元中国的世界海洋商贸中心": "泉州：宋元中国的世界海洋商贸中心",
            "普洱景迈山古茶林文化景观": "普洱景迈山古茶林",
            "北京中轴线": "北京中轴线",
            "西夏陵": "西夏陵",
            "黄龙风景名胜区": "黄龙风景名胜区",
            "九寨沟风景名胜区": "九寨沟",
            "武陵源风景名胜区": "武陵源风景名胜区",
            "云南三江并流保护区": "云南三江并流保护区",
            "四川大熊猫栖息地": "四川大熊猫栖息地",
            "中国南方喀斯特": "中国南方喀斯特",
            "三清山国家级风景名胜区": "三清山",
            "中国丹霞": "中国丹霞",
            "澄江化石地": "澄江化石地",
            "新疆天山": "天山山脉",
            "湖北神农架": "湖北神农架国家公园",
            "青海可可西里": "可可西里",
            "梵净山": "梵净山",
            "中国黄（渤）海候鸟栖息地": "中国黄（渤）海候鸟栖息地",
            "巴丹吉林沙漠": "巴丹吉林沙漠",
            "峨眉山—乐山大佛": "乐山大佛",
            "青城山—都江堰": "都江堰",
            "庐山国家级风景名胜区": "庐山"
        }
        for key, val in mapping.items():
            if key in site_name:
                return val
        return site_name

    def get_multi_region(site_name, default_prov):
        multi_region_map = {
            "长城": "北京市、河北省、甘肃省",
            "明清皇家宫殿": "北京市、辽宁省",
            "武夷山": "福建省、江西省",
            "明清皇家陵寝": "北京市、河北省、湖北省、江苏省、辽宁省",
            "高句丽": "吉林省、辽宁省",
            "喀斯特": "云南省、贵州省、重庆市、广西壮族自治区",
            "丹霞": "湖南省、广东省、福建省、江西省、浙江省、贵州省",
            "丝绸之路": "河南省、陕西省、甘肃省、新疆维吾尔自治区",
            "大运河": "北京市、天津市、河北省、山东省、江苏省、浙江省、安徽省、河南省",
            "土司遗址": "湖南省、湖北省、贵州省",
            "神农架": "湖北省、重庆市",
            "候鸟": "河北省、江苏省、辽宁省、山东省、上海市"
        }
        for key, multi_prov in multi_region_map.items():
            if key in site_name:
                return multi_prov
        return default_prov

    if st.session_state.detail_item:
        site_name = st.session_state.detail_item
        
        # 当用户查看某个遗产详情时，将其记录到历史足迹中
        if site_name not in st.session_state.search_history:
            st.session_state.search_history.append(site_name)
            
        base_info = next((item for item in all_heritage_list if item["name"] == site_name), None)
        
        display_region = get_multi_region(site_name, base_info["province"] if base_info else "跨省区/未获取")
        
        if st.button("返回清单检索"):
            st.session_state.detail_item = None
            st.rerun()
            
        st.markdown(f'''
            <div class="detail-header">
                <div class="detail-title">{site_name}</div>
                <div style="margin-top:10px;">
                    <span class="detail-tag">所在地区：{display_region}</span>
                    <span class="detail-tag">遗产类别：{base_info["category"] if base_info else "世界文化遗产"}</span>
                </div>
            </div>
        ''', unsafe_allow_html=True)
        
        wiki_text = ""
        wiki_img_url = None
        
        # 增加高级加载动画与图文抓取引擎
        with st.spinner(f"正在从云端知识库努力拉取【{site_name}】的详尽史料与影像，请稍候..."):
            if site_name in rich_encyclopedia:
                wiki_img_url = rich_encyclopedia[site_name].get("img")
                res = fetch_wikipedia_data(get_exact_wiki_title(site_name))
                wiki_text = res.get("text", "")
                if not wiki_img_url: wiki_img_url = res.get("image")
            elif "西递" in site_name or "宏村" in site_name:
                res1 = fetch_wikipedia_data("西递村")
                res2 = fetch_wikipedia_data("宏村村")
                wiki_img_url = res1.get("image") or res2.get("image")
                if res1.get("text"): wiki_text += "== 西递村 ==\n" + res1.get("text") + "\n\n"
                if res2.get("text"): wiki_text += "== 宏村村 ==\n" + res2.get("text")
            else:
                exact_title = get_exact_wiki_title(site_name)
                res = fetch_wikipedia_data(exact_title)
                wiki_text = res.get("text", "")
                wiki_img_url = res.get("image")

        # 成功抓取图片后，渲染高清绝美封面图
        if wiki_img_url:
            st.markdown(f'''
                <div style="width: 100%; height: 400px; overflow: hidden; border-radius: 12px; margin-bottom: 30px; box-shadow: 0 10px 30px rgba(0,0,0,0.1); border: 1px solid #EAD8C3;">
                    <img src="{wiki_img_url}" style="width: 100%; height: 100%; object-fit: cover;">
                </div>
            ''', unsafe_allow_html=True)
        else:
            # 没图的时候用雅致的国风色带过渡
            st.markdown('<div style="width: 100%; height: 8px; background: linear-gradient(90deg, #E6BA89, #8B3E04); border-radius: 4px; margin-bottom: 25px;"></div>', unsafe_allow_html=True)

        if wiki_text:
            paragraphs = wiki_text.split('\n')
            current_heading = None
            current_content = []
            skip_section = False 

            def flush_section(heading, content):
                if not content: 
                    return
                if heading:
                    if heading.startswith('===') and heading.endswith('==='):
                        title = heading.replace('=', '').strip()
                        st.markdown(f'<h4 style="color:#8B3E04; margin-top:20px; font-weight:bold;">{title}</h4>', unsafe_allow_html=True)
                    elif heading.startswith('==') and heading.endswith('=='):
                        title = heading.replace('=', '').strip()
                        st.markdown(f'<div class="section-title">{title}</div>', unsafe_allow_html=True)
                for line in content:
                    st.markdown(f'<div class="detail-text">{line}</div>', unsafe_allow_html=True)

            for p in paragraphs:
                p = p.strip()
                if not p: continue
                
                if (p.startswith('==') and p.endswith('==')) or (p.startswith('===') and p.endswith('===')):
                    if not skip_section:
                        flush_section(current_heading, current_content) 
                        
                    current_heading = p
                    current_content = []
                    
                    clean_title = p.replace('=', '').strip()
                    if clean_title in ["参见", "参看", "相关条目", "外部链接", "外部连结", "参考资料", "参考文献", "注释", "延伸阅读"]:
                        skip_section = True
                    else:
                        skip_section = False
                else:
                    if not skip_section:
                        current_content.append(p) 
            
            if not skip_section:
                flush_section(current_heading, current_content)
                
        else:
            st.warning(f"由于网络原因或词条对应差异，暂未从维基百科接口获取到【{site_name}】的详细全文数据。")

    else:
        st.markdown('<h1 class="main-title" style="font-size: 2.4rem;">国家级文化遗产名录检索</h1>', unsafe_allow_html=True)
        st.markdown('<div class="sub-title" style="margin-bottom: 20px;">全量 60 项独立数据已收录。支持按地区、类别、关键词查询。</div>', unsafe_allow_html=True)
        
        f_col1, f_col2, f_col3 = st.columns(3)
        with f_col1: search_prov = st.selectbox("所在地区", ["全部"] + list(heritage_data.keys()))
        with f_col2: search_cat = st.selectbox("遗产类别", ["全部", "世界文化遗产", "世界自然遗产", "文化与自然双重遗产"])
        with f_col3: search_kw = st.text_input("输入关键词检索", "")

        filtered_df = []
        for idx, item in enumerate(all_heritage_list):
            display_prov = get_multi_region(item["name"], item["province"])
            
            if search_prov != "全部" and search_prov not in display_prov: continue
            if search_cat != "全部" and item["category"] != search_cat: continue
            if search_kw and search_kw.lower() not in item["name"].lower(): continue
            
            filtered_df.append({"序号": idx+1, "名称": item["name"], "类别": item["category"], "所在地区": display_prov})
            
        if not filtered_df:
            st.warning("未找到匹配的遗产，请尝试放宽筛选条件。")
        else:
            df = pd.DataFrame(filtered_df)
            html_table = df.to_html(index=False, classes='custom-table', escape=False)
            html_table = html_table.replace('<th>序号</th>', '<th style="width: 10%;">序号</th>')
            st.markdown(html_table, unsafe_allow_html=True)
            
            st.write("---")
            selected_site = st.selectbox("请选择您要查看的遗产名称，点击下方按钮查阅详细档案：", [row["名称"] for row in filtered_df])
            if st.button("进入详情页", type="primary"):
                st.session_state.detail_item = selected_site
                st.rerun()

# ================= 页面四：AI 大模型  =================
elif st.session_state.current_page == "AI 智游":
    
    client = OpenAI(
        api_key="sk-6f9be56913e14cb28d4fb146a6606ae9", 
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    )

    st.markdown("""
        <style>
        /* 保护导航栏，取消大字号，与全局原生字体绝对一致 */
        div[data-testid="stHorizontalBlock"]:first-of-type div.stButton > button {
            border: none !important; background-color: transparent !important; color: #5C1D16 !important; 
            font-weight: normal !important; border-bottom: 3px solid transparent !important; 
            border-radius: 0 !important; padding: 12px 0 !important; min-height: auto !important;
        }
        div[data-testid="stHorizontalBlock"]:first-of-type div.stButton > button p {
            font-size: 1rem !important; color: #5C1D16 !important; font-weight: normal !important; margin: 0 !important; text-align: center !important;
        }
        div[data-testid="stHorizontalBlock"]:first-of-type div.stButton > button:hover {
            border-bottom: 3px solid #8B3E04 !important; color: #8B3E04 !important; background-color: #FDF8F5 !important;
        }

        /* 精确锁定最内层盒子，只让快捷提示框吸底 */
        div[data-testid="stVerticalBlock"]:has(#quick-prompt-marker):not(:has(div[data-testid="stVerticalBlock"]:has(#quick-prompt-marker))) {
            position: fixed; bottom: 78px; left: 50%; transform: translateX(-50%); width: 100%; max-width: 704px;
            z-index: 999; background: rgba(253, 248, 245, 0.95); padding: 15px 20px 5px 20px;
            border-radius: 12px; box-shadow: 0px -4px 15px rgba(0,0,0,0.06); backdrop-filter: blur(10px); border: 1px solid #EAD8C3;
        }
        
        /* 只针对最内层的快捷按钮加细框和缩小字体 */
        div[data-testid="stVerticalBlock"]:has(#quick-prompt-marker):not(:has(div[data-testid="stVerticalBlock"]:has(#quick-prompt-marker))) div[data-testid="stButton"] > button {
            padding: 5px 10px !important; min-height: 35px !important; border-radius: 8px !important;
            background-color: #FFFFFF !important; border: 1px solid #EAD8C3 !important; transition: all 0.2s;
        }
        div[data-testid="stVerticalBlock"]:has(#quick-prompt-marker):not(:has(div[data-testid="stVerticalBlock"]:has(#quick-prompt-marker))) div[data-testid="stButton"] > button p {
            font-size: 0.9rem !important; color: #555 !important; font-weight: normal !important; margin: 0 !important; text-align: center !important;
        }
        div[data-testid="stVerticalBlock"]:has(#quick-prompt-marker):not(:has(div[data-testid="stVerticalBlock"]:has(#quick-prompt-marker))) div[data-testid="stButton"] > button:hover {
            border-color: #8B3E04 !important; background-color: #FDF8F5 !important;
        }
        div[data-testid="stVerticalBlock"]:has(#quick-prompt-marker):not(:has(div[data-testid="stVerticalBlock"]:has(#quick-prompt-marker))) div[data-testid="stButton"] > button:hover p {
            color: #8B3E04 !important; font-weight: bold !important;
        }
        
        .block-container { padding-bottom: 220px !important; }
        </style>
    """, unsafe_allow_html=True)

    st.markdown('<h1 class="main-title">AI：智游遗迹</h1>', unsafe_allow_html=True)
    st.markdown('<h3 class="sub-title">您的专属大模型文化导游，搭载阿里云千问核心引擎。</h3>', unsafe_allow_html=True)
    
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {"role": "assistant", "content": "您好！我是华夏智导。关于这 60 项世界遗产的任何风貌、历史故事或行程规划，您都可以向我提问哦！"}
        ]

    for message in st.session_state.messages:
        if message["role"] == "user":
            # 将用户气泡字体统一调回 1rem 标准大小
            st.markdown(f'''
                <div style="display: flex; align-items: flex-start; justify-content: flex-end; margin-bottom: 20px;">
                    <div style="background-color: #F4EBE1; color: #5C1D16; padding: 12px 18px; border-radius: 15px 0px 15px 15px; max-width: 75%; font-size: 1rem; line-height: 1.6; box-shadow: 0 2px 5px rgba(0,0,0,0.05);">
                        {message["content"]}
                    </div>
                    <div style="margin-left: 15px; background-color: #8B3E04; border-radius: 50%; width: 45px; height: 45px; display: flex; align-items: center; justify-content: center; box-shadow: 0 2px 5px rgba(0,0,0,0.2);">
                        <svg viewBox="0 0 24 24" width="28" height="28" fill="white"><path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/></svg>
                    </div>
                </div>
            ''', unsafe_allow_html=True)
        else:
            with st.chat_message("assistant"):
                st.markdown(message["content"])

    # 快捷提示框容器 
    with st.container():
        st.markdown("<div id='quick-prompt-marker'></div><p style='margin-top: 0px; margin-bottom: 10px; color: #8B3E04; font-size: 0.95rem; font-weight: bold;'>💡 猜你想问</p>", unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        quick_prompt = None
        if c1.button("规划三天两夜西湖行程", use_container_width=True): quick_prompt = "帮我规划三天两夜的西湖行程"
        if c2.button("长城为什么被称为奇迹？", use_container_width=True): quick_prompt = "长城为什么被称为世界奇迹？"
        if c3.button("介绍布达拉宫的建筑特色", use_container_width=True): quick_prompt = "介绍一下布达拉宫的建筑特色"

    prompt = st.chat_input("例如：用50字简单介绍一下布达拉宫...")
    user_input = quick_prompt or prompt

    if user_input:
        st.session_state.messages.append({"role": "user", "content": user_input})
        # 新发出的用户气泡同样调回 1rem 标准大小
        st.markdown(f'''
            <div style="display: flex; align-items: flex-start; justify-content: flex-end; margin-bottom: 20px;">
                <div style="background-color: #F4EBE1; color: #5C1D16; padding: 12px 18px; border-radius: 15px 0px 15px 15px; max-width: 75%; font-size: 1rem; line-height: 1.6; box-shadow: 0 2px 5px rgba(0,0,0,0.05);">
                    {user_input}
                </div>
                <div style="margin-left: 15px; background-color: #8B3E04; border-radius: 50%; width: 45px; height: 45px; display: flex; align-items: center; justify-content: center; box-shadow: 0 2px 5px rgba(0,0,0,0.2);">
                    <svg viewBox="0 0 24 24" width="28" height="28" fill="white"><path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/></svg>
                </div>
            </div>
        ''', unsafe_allow_html=True)

        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            full_response = ""
            try:
                system_prompt = {"role": "system", "content": "你是一个专业的中国世界遗产智能导游，名叫“华夏智导”。你需要用热情、专业、生动的语言回答游客关于中国60项世界遗产的问题。"}
                api_messages = [system_prompt] + [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages]
                
                response = client.chat.completions.create(
                    model="qwen-plus",
                    messages=api_messages,
                    stream=True,
                )
                for chunk in response:
                    if chunk.choices[0].delta.content is not None:
                        full_response += chunk.choices[0].delta.content
                        message_placeholder.markdown(full_response + "▌")
                message_placeholder.markdown(full_response)
            except Exception as e:
                full_response = f"抱歉，导游大脑暂时短路了（API连接超时或报错），请稍后再试哦~"
                message_placeholder.error(f"报错详情：{str(e)}")
        
        st.session_state.messages.append({"role": "assistant", "content": full_response})

# ================= 页面五：寻迹社区  =================
elif st.session_state.current_page == "寻迹社区":
    import random
    
    COMMENTS_FILE = "posts.json"

    def load_posts():
        if os.path.exists(COMMENTS_FILE):
            try:
                with open(COMMENTS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if data and len(data) >= 5: 
                        return data
            except Exception:
                pass
        
        default_posts = [
            {
                "id": "post_demo_1", "title": "烟雨下江南，西湖绝美打卡点！", "name": "江南烟雨", "avatar": "🍵", "time": "2024-05-21 14:15", 
                "content": "刚跟着 AI 导游做了一份去杭州西湖的攻略，风景真的太美了！雷峰夕照绝绝子，强烈建议大家一定要去坐一下摇橹船！给大家分享一张我的打卡照片！", 
                "image": img3, "likes": 128, "liked_by": [],
                "comments": [{"c_id": "c1", "name": "历史发烧友", "avatar": "🐉", "content": "求一份详细的游览路线！", "time": "2024-05-21 15:20", "up": 12, "down": 0, "up_by": [], "down_by": []}]
            },
            {
                "id": "post_demo_2", "title": "紫禁城的红墙黄瓦，中式审美的天花板", "name": "故宫在逃格格", "avatar": "🌸", "time": "2024-05-18 09:20", 
                "content": "北京及沈阳的明清皇家宫殿真的是去多少次都不会腻的地方！尤其是下了雪之后，红墙白雪简直绝美。用这个系统查了一下背后的历史构造，对古代匠人的智慧佩服得五体投地！", 
                "image": img2, "likes": 256, "liked_by": [],
                "comments": [{"c_id": "c2", "name": "古建研究僧", "avatar": "⛩️", "content": "榫卯结构真的是神级发明！", "time": "2024-05-18 11:15", "up": 34, "down": 0, "up_by": [], "down_by": []}]
            },
            {
                "id": "post_demo_3", "title": "不到长城非好汉，一眼千年的震撼！", "name": "历史发烧友", "avatar": "🐉", "time": "2024-05-20 10:30", 
                "content": "周末特地去爬了慕田峪长城，站在烽火台上吹着风，看着巨龙蜿蜒在群山之间，那种震撼感真的是直击心灵的！", 
                "image": img1, "likes": 89, "liked_by": [], "comments": []
            },
            {
                "id": "post_demo_4", "title": "秦始皇陵地下军阵，这才是第八大奇迹", "name": "寻迹探秘者", "avatar": "🐯", "time": "2024-05-15 16:45", 
                "content": "特地去西安看了秦始皇陵及兵马俑坑，千人千面，极其震撼。站在坑边，仿佛能听到两千多年前金戈铁马的呼啸声，古人的伟力让人敬畏！", 
                "image": img4, "likes": 198, "liked_by": [], "comments": []
            },
            {
                "id": "post_demo_5", "title": "日光之城，布达拉宫朝圣之旅", "name": "雪域行者", "avatar": "🏮", "time": "2024-05-12 11:10", 
                "content": "站在拉萨的阳光下，仰望拉萨布达拉宫历史建筑群的红白墙，心灵得到了前所未有的洗涤。每一块石头都刻着信仰的重量。", 
                "image": img5, "likes": 312, "liked_by": [], "comments": []
            }
        ]
        with open(COMMENTS_FILE, "w", encoding="utf-8") as f:
            json.dump(default_posts, f, ensure_ascii=False, indent=4)
        return default_posts

    def save_posts(posts):
        with open(COMMENTS_FILE, "w", encoding="utf-8") as f:
            json.dump(posts, f, ensure_ascii=False, indent=4)

    # 核心状态机初始化
    if 'user_profile' not in st.session_state: st.session_state.user_profile = {"id": "user_" + str(os.urandom(4).hex()), "name": "神秘游客", "avatar": "🐼"}
    if 'view_post_id' not in st.session_state: st.session_state.view_post_id = None
    if 'followed_users' not in st.session_state: st.session_state.followed_users = []
    if 'filter_user' not in st.session_state: st.session_state.filter_user = None 
    if 'rec_users' not in st.session_state: st.session_state.rec_users = [] 
    
    if 'toast_msg' not in st.session_state: st.session_state.toast_msg = None
    if 'reply_target' not in st.session_state: st.session_state.reply_target = None
    
    if st.session_state.toast_msg:
        st.toast(st.session_state.toast_msg, icon="🎉")
        st.session_state.toast_msg = None
        
    def render_avatar(avatar_data, size="45px", font_size="1.5rem"):
        if avatar_data.startswith("data:image"): return f'<img src="{avatar_data}" style="width:{size}; height:{size}; border-radius:50%; object-fit:cover; border: 2px solid #EAD8C3; flex-shrink: 0;">'
        else: return f'<div style="width:{size}; height:{size}; border-radius:50%; background-color:#FDF8F5; display:flex; align-items:center; justify-content:center; font-size:{font_size}; border: 2px solid #EAD8C3; flex-shrink: 0;">{avatar_data}</div>'

    def set_view_post(pid): st.session_state.view_post_id = pid
    def clear_view_post(): 
        st.session_state.view_post_id = None
        st.session_state.reply_target = None
        
    def set_filter_user(uname): st.session_state.filter_user = uname
    def clear_filter_user(): st.session_state.filter_user = None
    
    def toggle_follow(uname):
        if uname in st.session_state.followed_users:
            st.session_state.followed_users.remove(uname)
        else:
            st.session_state.followed_users.append(uname)
            st.session_state.toast_msg = f"已成功关注 {uname}！"
            
    def set_reply(uname):
        st.session_state.reply_target = uname
        
    def clear_reply():
        st.session_state.reply_target = None

    st.markdown("""
        <style>
        header[data-testid="stHeader"] {display: none !important;}
        [data-testid="collapsedControl"] {display: none !important;}
        [data-testid="stSidebar"] {display: none !important;}
        .block-container { padding-top: 0rem !important; padding-bottom: 1rem !important; max-width: 95% !important; margin-top: 0rem !important;}
        
        *:focus { outline: none !important; box-shadow: none !important; }
        button:focus { outline: none !important; box-shadow: none !important; }
        button:active { outline: none !important; box-shadow: none !important; }
        
        div[data-testid="stHorizontalBlock"]:first-of-type div.stButton > button {
            border: none !important; background-color: transparent !important; color: #5C1D16 !important; 
            font-size: 1.25rem !important; font-weight: normal !important; border-bottom: 3px solid transparent !important; 
            border-radius: 0 !important; padding: 12px 0 !important;
        }
        div[data-testid="stHorizontalBlock"]:first-of-type div.stButton > button p { font-weight: normal !important; text-align: center !important; margin: 0 !important; }
        div[data-testid="stHorizontalBlock"]:first-of-type div.stButton > button:hover { border-bottom: 3px solid #8B3E04 !important; color: #8B3E04 !important; background-color: #FDF8F5 !important; }
        
        .community-title { font-size: 2.2rem; font-weight: 900; color: #333; margin-bottom: 5px; }
        .community-subtitle { font-size: 1.1rem; color: #666; margin-bottom: 30px; }
        .section-header { font-size: 1.35rem; font-weight: 900; color: #222; padding-left: 12px; border-left: 5px solid #8B3E04; margin-bottom: 18px; margin-top: 5px; display: flex; align-items: center;}
        
        .feed-card { background-color: #FFFFFF; border: 1px solid #EAD8C3; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 10px rgba(0,0,0,0.03); transition: transform 0.25s, box-shadow 0.25s; margin-bottom: 15px; }
        .feed-card:hover { transform: translateY(-4px); box-shadow: 0 8px 25px rgba(0,0,0,0.08); }
        .feed-card div[data-testid="stButton"] > button { width: 100% !important; border: none !important; background-color: transparent !important; border-radius: 0 !important; padding: 15px 15px 5px 15px !important; min-height: 70px !important; }
        .feed-card div[data-testid="stButton"] > button p { text-align: left !important; font-weight: 900 !important; font-size: 1.15rem !important; color: #222 !important; white-space: normal !important; line-height: 1.4 !important; margin: 0 !important; }
        
        .invisible-text-btn div[data-testid="stButton"] > button {
            border: none !important; background: transparent !important; padding: 0 !important; margin: 0 !important; 
            height: auto !important; min-height: 0 !important; justify-content: flex-start !important;
        }
        .invisible-text-btn div[data-testid="stButton"] > button p {
            color: #333 !important; font-weight: bold !important; font-size: 0.95rem !important; text-align: left !important; margin: 0 !important;
        }
        .invisible-text-btn div[data-testid="stButton"] > button:hover p { color: #C68244 !important; }

        /*  热门标题按钮：强制去边距，配合 Flexbox 实现天花板对齐 */
        .hot-title-btn div[data-testid="stButton"] > button {
            border: none !important; background: transparent !important; padding: 0 !important; margin: 0 !important; 
            height: auto !important; min-height: 0 !important; justify-content: flex-start !important;
        }
        .hot-title-btn div[data-testid="stButton"] > button p {
            color: #333 !important; font-weight: bold !important; font-size: 0.95rem !important; text-align: left !important; 
            margin: 0 !important; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; line-height: 1.3 !important;
        }
        .hot-title-btn div[data-testid="stButton"] > button:hover p { color: #C68244 !important; }

        .back-btn div[data-testid="stButton"] > button { border: 1px solid #EAD8C3 !important; background-color: #FFFFFF !important; color: #555 !important; border-radius: 8px !important; padding: 8px 15px !important; }
        .back-btn div[data-testid="stButton"] > button:hover { border-color: #8B3E04 !important; color: #8B3E04 !important; }
        .back-btn div[data-testid="stButton"] > button p { font-weight: normal !important; text-align: center !important;}
        
        div.stButton > button { border: 1px solid #EAD8C3; background-color: #FFFFFF; color: #333; border-radius: 8px; padding: 8px 15px; transition: all 0.3s; }
        div.stButton > button:hover { border-color: #8B3E04; color: #8B3E04; }
        div.stButton > button p { font-weight: normal !important; text-align: center !important;}
        
        div.stButton > button[data-baseweb="button"][kind="primary"] { background-color: #FFF2F2 !important; border: 1px solid #E06C75 !important; color: #E06C75 !important; }
        div.stButton > button[kind="primary"] p { color: #E06C75 !important; font-weight: bold !important; text-align: center !important;}
        
        div.stButton > button[data-baseweb="button"][kind="secondary"] { border: 1px solid #EAD8C3 !important; background-color: #FFFFFF !important; color: #555 !important; }
        div.stButton > button[kind="secondary"] p { font-weight: normal !important; text-align: center !important;}
        div.stButton > button[kind="secondary"]:hover { border-color: #8B3E04 !important; }
        
        .icon-action-btn div[data-testid="stButton"] > button { 
            padding: 0px 5px !important; min-height: 24px !important; border-radius: 6px !important; 
            border: none !important; background-color: transparent !important; color: #888 !important;
        }
        .icon-action-btn div[data-testid="stButton"] > button:hover { color: #C68244 !important; background-color: #FDF8F5 !important;}
        .icon-action-btn div[data-testid="stButton"] > button[kind="primary"] { color: #E06C75 !important; font-weight: bold !important; background-color: transparent !important;}
        .icon-action-btn div[data-testid="stButton"] > button p { font-size: 0.8rem !important; margin: 0 !important;}
        
        .mini-action-btn div[data-testid="stButton"] > button { padding: 2px 5px !important; min-height: 28px !important; font-size: 0.8rem !important; border-radius: 15px !important; margin-top: 6px !important;}
        .mini-action-btn div[data-testid="stButton"] > button p { font-size: 0.8rem !important; margin: 0 !important; font-weight: bold !important;}
        
        .detail-post-box {background-color: #FFFFFF; border-radius: 12px; padding: 30px; box-shadow: 0 4px 20px rgba(0,0,0,0.04); border: 1px solid #F0F0F0;}
        .detail-author-row {display: flex; align-items: center; gap: 15px; margin-bottom: 20px;}
        .detail-content {font-size: 1.15rem; color: #333; line-height: 1.8; margin-bottom: 20px; text-align: justify;}
        .detail-img {max-width: 100%; border-radius: 8px; margin-top: 15px; margin-bottom: 20px; box-shadow: 0 4px 15px rgba(0,0,0,0.1);}
        </style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="community-title">寻迹社区 | 文化传承交流区</div>', unsafe_allow_html=True)
    st.markdown('<div class="community-subtitle">在这里留下您的足迹，与五湖四海的文化爱好者交流心得。</div>', unsafe_allow_html=True)

    with st.expander("我的资料设置 (发表动态前，请先完善您的专属名片)", expanded=False):
        col_av, col_name, col_upload = st.columns([0.5, 1.5, 2])
        with col_av:
            st.markdown("<div style='margin-bottom:10px; color:#555; font-size:0.9rem; font-weight:bold;'>当前头像</div>", unsafe_allow_html=True)
            st.markdown(render_avatar(st.session_state.user_profile["avatar"], "70px", "2.2rem"), unsafe_allow_html=True)
        with col_name:
            new_name = st.text_input("我的专属昵称", value=st.session_state.user_profile["name"], max_chars=15)
            new_emoji = st.selectbox("更换基础国风头像", ["保持原样", "🐼", "🐉", "🍵", "🌸", "🏮", "⛩️", "🐯"])
        with col_upload:
            uploaded_av = st.file_uploader("或直接上传本地照片作为头像", type=["png", "jpg", "jpeg"])
            
        if st.button("保存更新档案", type="primary"):
            st.session_state.user_profile["name"] = new_name.strip() or "神秘游客"
            if uploaded_av:
                st.session_state.user_profile["avatar"] = "data:image/jpeg;base64," + base64.b64encode(uploaded_av.read()).decode('utf-8')
            elif new_emoji != "保持原样":
                st.session_state.user_profile["avatar"] = new_emoji
            st.success("资料更新成功！赶快去发帖吧！")
            st.rerun()
        # === (接在资料更新成功的 st.rerun() 后面，st.write("---") 的前面) ===

        # 足迹收集成就系统
        st.markdown("<hr style='margin: 15px 0; border-top: 1px dashed #CCC;'>", unsafe_allow_html=True)
        st.markdown("<div style='font-size:1.1rem; font-weight:900; color:#5C1D16; margin-bottom:15px;'>🏅 我的华夏数字护照 (百科探索成就)</div>", unsafe_allow_html=True)
        
        # 联动你在百科留下的足迹数据
        visited_sites = st.session_state.get('search_history', [])
        total_sites = 60
        visited_count = len(set(visited_sites))
        progress = int((visited_count / total_sites) * 100) if total_sites > 0 else 0
        
        # 极具游戏感的进度条
        st.markdown(f"""
            <div style="display:flex; justify-content:space-between; margin-bottom:5px; font-size:0.9rem; color:#555; font-weight:bold;">
                <span>已点亮世界遗产：{visited_count}/{total_sites}</span>
                <span style="color:#C68244;">{progress}%</span>
            </div>
            <div style="width:100%; background:#EEEEEE; border-radius:10px; height:12px; margin-bottom:20px; overflow:hidden; box-shadow: inset 0 1px 3px rgba(0,0,0,0.1);">
                <div style="width:{progress}%; background:linear-gradient(90deg, #E6BA89, #8B3E04); height:100%; border-radius:10px; transition:width 0.5s;"></div>
            </div>
        """, unsafe_allow_html=True)
        
        # 精选 6 个顶级地标作为勋章展示墙
        target_badges = ["长城", "明清皇家宫殿", "秦始皇陵及兵马俑坑", "西湖", "拉萨布达拉宫历史建筑群", "黄山"]
        badge_icons = ["🧱", "🏯", "🗿", "🚣", "🕍", "⛰️"]
        
        b_cols = st.columns(6)
        for idx, badge in enumerate(target_badges):
            # 核心判定：是否在足迹列表中
            is_lit = any(badge in site for site in visited_sites) 
            
            # CSS 状态机：点亮 vs 未点亮
            opacity = "1" if is_lit else "0.4"
            filter_css = "grayscale(0%)" if is_lit else "grayscale(100%)"
            bg_color = "#FFF8F0" if is_lit else "#FAFAFA"
            border_color = "#C68244" if is_lit else "#EEEEEE"
            text_color = "#8B3E04" if is_lit else "#999999"
            
            with b_cols[idx]:
                st.markdown(f'''
                    <div style="display:flex; flex-direction:column; align-items:center; justify-content:center; 
                                opacity:{opacity}; filter:{filter_css}; background:{bg_color}; border:2px solid {border_color}; 
                                border-radius:12px; padding:15px 2px; box-shadow:0 4px 10px rgba(0,0,0,0.05); transition:all 0.3s; height: 110px;">
                        <div style="font-size:2rem; margin-bottom:5px;">{badge_icons[idx]}</div>
                        <div style="font-size:0.7rem; font-weight:bold; color:{text_color}; text-align:center; line-height:1.2;">{badge[:4]}<br>{badge[4:] if len(badge)>4 else ""}</div>
                    </div>
                ''', unsafe_allow_html=True)
            
        st.write("---")
        if st.session_state.followed_users:
            st.markdown("<div style='font-size:0.95rem; font-weight:bold; color:#555; margin-bottom:15px;'>我关注的达人：</div>", unsafe_allow_html=True)
            posts_for_avatar = load_posts()
            av_dict = {p["name"]: p["avatar"] for p in posts_for_avatar}
            
            u_cols = st.columns(2) 
            for i, fu in enumerate(st.session_state.followed_users):
                with u_cols[i % 2]: 
                    cls_name = f"ucard_{i}"
                    st.markdown(f'<style>span.{cls_name} + div[data-testid="stHorizontalBlock"] {{ background: #FAFAFA; border: 1px solid #EEEEEE; border-radius: 8px; padding: 8px 12px; margin-bottom: 12px; box-shadow: 0 2px 4px rgba(0,0,0,0.02); align-items: center; transition: all 0.2s; }} span.{cls_name} + div[data-testid="stHorizontalBlock"]:hover {{ background: #FFFFFF; border-color: #EAD8C3; box-shadow: 0 4px 8px rgba(0,0,0,0.05); }}</style><span class="{cls_name}"></span>', unsafe_allow_html=True)
                    # 极简版 ID 布局，没有多余头像
                    uc1, uc2 = st.columns([3, 1.2])
                    with uc1:
                        st.markdown('<div class="invisible-text-btn" style="margin-top: 4px;">', unsafe_allow_html=True)
                        st.button(f"👤 {fu}", key=f"go_my_{fu}", on_click=set_filter_user, args=(fu,), use_container_width=True)
                        st.markdown('</div>', unsafe_allow_html=True)
                    with uc2:
                        st.markdown('<div class="mini-action-btn">', unsafe_allow_html=True)
                        st.button("已关注", key=f"unfol_{fu}", on_click=toggle_follow, args=(fu,), type="secondary", use_container_width=True)
                        st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.markdown("""
            <div style="padding: 20px; text-align: center; color: #888; background: #FAFAFA; border-radius: 8px; border: 1px dashed #CCC;">
                <div style="font-size: 2rem; margin-bottom: 10px;">🍃</div>
                您还没有关注任何达人哦~<br>去广场找找同好，或者在推荐列表中看看吧！
            </div>
            """, unsafe_allow_html=True)

    posts_data = load_posts()

    if st.session_state.view_post_id is None:
        
        col_form, col_board = st.columns([1, 1.8])

        with col_form:
            st.markdown('<div class="section-header">发布新帖子</div>', unsafe_allow_html=True)
            with st.container():
                with st.form("post_form", clear_on_submit=True):
                    post_title = st.text_input("帖子标题", placeholder="给你的分享起个响亮的标题...", max_chars=30)
                    user_content = st.text_area("正文内容", placeholder="分享一下您最喜欢的世界遗产故事吧...", height=120)
                    user_image = st.file_uploader("上传封面/打卡照片 (可选)", type=["png", "jpg", "jpeg"])
                    
                    st.markdown(f"<div style='font-size:0.9rem; color:#888; margin-bottom:10px;'>将以 <b>{st.session_state.user_profile['name']}</b> 的身份发布</div>", unsafe_allow_html=True)
                    submit_btn = st.form_submit_button("立即发布", use_container_width=True)
                    
                    if submit_btn:
                        if not user_content.strip() or not post_title.strip():
                            st.error("标题和正文都不能为空哦！")
                        else:
                            img_b64 = None
                            if user_image is not None:
                                img_b64 = "data:image/jpeg;base64," + base64.b64encode(user_image.read()).decode('utf-8')
                                
                            new_post = {
                                "id": "post_" + str(os.urandom(4).hex()),
                                "title": post_title.strip(),
                                "name": st.session_state.user_profile["name"],
                                "avatar": st.session_state.user_profile["avatar"], 
                                "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
                                "content": user_content.strip(),
                                "image": img_b64,
                                "likes": 0,
                                "liked_by": [],
                                "comments": []
                            }
                            posts_data.insert(0, new_post)
                            save_posts(posts_data)
                            st.success("帖子发布成功！")
                            st.rerun()

            def get_post_score(post):
                base_score = len(post.get("liked_by", [])) + post.get("likes", 0)
                bonus = 0
                if 'search_history' in st.session_state:
                    for kw in st.session_state.search_history:
                        if kw in post['title'] or kw in post['content']:
                            bonus += 1000 
                return base_score + bonus

            st.markdown('<div class="section-header" style="margin-top: 35px;">热门推荐</div>', unsafe_allow_html=True)
            hot_posts = sorted(posts_data, key=get_post_score, reverse=True)[:3]
            
            for i, hp in enumerate(hot_posts):
                cls_name = f"hotcard_{i}"
                #  终极魔法：让右侧信息框的高度自适应并且采用 flex 两端对齐！绝对顶部、绝对底部！
                st.markdown(f'''
                    <style>
                    span.{cls_name} + div[data-testid="stHorizontalBlock"] {{ background: #FFFFFF; border: 1px solid #EEEEEE; border-radius: 8px; padding: 10px; margin-bottom: 12px; box-shadow: 0 2px 5px rgba(0,0,0,0.02); align-items: stretch; transition: all 0.2s; }} 
                    span.{cls_name} + div[data-testid="stHorizontalBlock"]:hover {{ transform: translateY(-2px); border-color:#C68244; box-shadow: 0 4px 10px rgba(0,0,0,0.05); }}
                    /* 强制右侧容器拉伸并上下对齐 */
                    span.{cls_name} + div[data-testid="stHorizontalBlock"] > div:nth-child(2) > div[data-testid="stVerticalBlock"] {{ display: flex; flex-direction: column; justify-content: space-between; height: 100%; padding-top: 2px; padding-bottom: 2px; }}
                    </style><span class="{cls_name}"></span>
                ''', unsafe_allow_html=True)
                hc1, hc2 = st.columns([1, 3.5])
                with hc1:
                    if hp.get("image"):
                        st.markdown(f'<img src="{hp["image"]}" style="width: 100%; aspect-ratio: 1/1; object-fit: cover; border-radius: 6px; display: block;">', unsafe_allow_html=True)
                    else:
                        st.markdown(f'<div style="width: 100%; aspect-ratio: 1/1; background: #FDF8F5; border-radius: 6px; display: flex; align-items: center; justify-content: center; color: #C68244; font-size: 1.2rem;">📜</div>', unsafe_allow_html=True)
                with hc2:
                    st.markdown('<div class="hot-title-btn">', unsafe_allow_html=True)
                    # 这个按钮依然完美保持跳转功能
                    st.button(f"{hp['title']}", key=f"hot_btn_{hp['id']}", on_click=set_view_post, args=(hp['id'],), use_container_width=True)
                    st.markdown('</div>', unsafe_allow_html=True)
                    
                    is_recommended = False
                    if 'search_history' in st.session_state:
                        is_recommended = any(kw in hp['title'] or kw in hp['content'] for kw in st.session_state.search_history)
                    
                    tag_html = "<span style='color:#C68244; background:#FDF8F5; padding:1px 4px; border-radius:4px; font-size:0.65rem; margin-right:5px;'>猜你喜欢</span>" if is_recommended else ""
                    st.markdown(f"<div style='display: flex; justify-content: space-between; align-items: flex-end; font-size: 0.75rem; color: #888; margin: 0;'><div style='display:flex; align-items:center;'>{tag_html}<span style='white-space: nowrap; overflow: hidden; text-overflow: ellipsis; font-weight: 500;'>{hp['name']}</span></div><span style='color: #E06C75; font-weight: 900; flex-shrink: 0;'>❤️ {len(hp.get('liked_by', [])) + hp.get('likes', 0)}</span></div>", unsafe_allow_html=True)

            head_c1, head_c2 = st.columns([2.5, 1])
            with head_c1:
                st.markdown('<div class="section-header" style="margin-top: 35px;">推荐关注达人</div>', unsafe_allow_html=True)
            with head_c2:
                st.markdown('<div style="margin-top: 38px;">', unsafe_allow_html=True)
                if st.button("换一批", use_container_width=True):
                    st.session_state.rec_users = []
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)
            
            if not st.session_state.rec_users:
                all_users = {}
                for p in posts_data:
                    if p["name"] != st.session_state.user_profile["name"] and p["name"] not in st.session_state.followed_users:
                        if p["name"] not in all_users:
                            all_users[p["name"]] = {"av": p["avatar"], "desc": f"发布了《{p['title'][:8]}...》"}
                
                default_strangers = {"古建研究僧": {"av": "⛩️", "desc": "记录每一块青砖黛瓦"}, "背包客小王": {"av": "🐼", "desc": "走遍中国50处世界遗产"}, "丝路旅人": {"av": "🐫", "desc": "重走千年丝绸之路"}, "摄影小达人": {"av": "📷", "desc": "用镜头定格历史的瞬间"}, "寻迹探秘者": {"av": "🐯", "desc": "揭开秦始皇陵的秘密"}}
                for k, v in default_strangers.items():
                    if k != st.session_state.user_profile["name"] and k not in st.session_state.followed_users and k not in all_users:
                        all_users[k] = v
                        
                user_list = list(all_users.items())
                st.session_state.rec_users = random.sample(user_list, min(3, len(user_list)))
            
            for j, (uname, uinfo) in enumerate(st.session_state.rec_users):
                cls_name = f"reccard_{j}"
                st.markdown(f'<style>span.{cls_name} + div[data-testid="stHorizontalBlock"] {{ background: #FAFAFA; border: 1px solid #EEEEEE; border-radius: 10px; padding: 10px 12px; margin-bottom: 12px; align-items: center; transition: all 0.2s; }} span.{cls_name} + div[data-testid="stHorizontalBlock"]:hover {{ border-color:#C68244; background:#FFFFFF; box-shadow: 0 2px 8px rgba(0,0,0,0.03); }}</style><span class="{cls_name}"></span>', unsafe_allow_html=True)
                fc1, fc2, fc3, fc4 = st.columns([0.8, 2, 1.2, 1.2])
                with fc1: 
                    st.markdown(render_avatar(uinfo["av"], "35px", "1.2rem"), unsafe_allow_html=True)
                with fc2: 
                    st.markdown(f"<div style='font-weight:bold; font-size:0.9rem; color:#333; margin-bottom:2px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;'>{uname}</div><div style='font-size:0.75rem; color:#999; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;'>{uinfo['desc']}</div>", unsafe_allow_html=True)
                with fc3:
                    st.markdown('<div class="mini-action-btn">', unsafe_allow_html=True)
                    st.button("看主页", key=f"go_rec_{uname}", on_click=set_filter_user, args=(uname,), use_container_width=True)
                    st.markdown('</div>', unsafe_allow_html=True)
                with fc4:
                    is_following = uname in st.session_state.followed_users
                    btn_label = "已关注" if is_following else "关注"
                    st.markdown('<div class="mini-action-btn">', unsafe_allow_html=True)
                    st.button(btn_label, key=f"follow_rec_{uname}", on_click=toggle_follow, args=(uname,), type="secondary" if is_following else "primary", use_container_width=True)
                    st.markdown('</div>', unsafe_allow_html=True)

        with col_board:
            if st.session_state.filter_user:
                st.markdown(f'<div class="section-header">正在查看【{st.session_state.filter_user}】的个人主页</div>', unsafe_allow_html=True)
                st.markdown('<div class="back-btn" style="margin-bottom:20px;">', unsafe_allow_html=True)
                st.button("返回全部动态", on_click=clear_filter_user)
                st.markdown('</div>', unsafe_allow_html=True)
                display_posts = [p for p in posts_data if p["name"] == st.session_state.filter_user]
                if not display_posts:
                    st.info("TA还没有发布任何帖子哦~ 期待TA的第一篇分享！")
            else:
                c_header, c_search = st.columns([1, 1])
                with c_header:
                    st.markdown('<div class="section-header">最新帖子</div>', unsafe_allow_html=True)
                with c_search:
                    search_kw = st.text_input("搜索", placeholder="🔍 搜索标题或内容...", label_visibility="collapsed")
                
                display_posts = posts_data
                if search_kw:
                    display_posts = [p for p in posts_data if search_kw.lower() in p["title"].lower() or search_kw.lower() in p["content"].lower()]
                
                if not display_posts:
                    st.info("没有找到相关帖子，换个关键词试试吧！或者您来发布第一篇！")
            
            cols = st.columns(2)
            for idx, post in enumerate(display_posts):
                with cols[idx % 2]:
                    if "liked_by" not in post: post["liked_by"] = []
                    likes_count = len(post.get("liked_by", [])) + post.get("likes", 0)
                    
                    st.markdown('<div class="feed-card">', unsafe_allow_html=True)
                    
                    if post.get("image"):
                        st.markdown(f'<img src="{post["image"]}" style="width:100%; height:180px; object-fit:cover; display:block; border-bottom: 1px solid #F0F0F0;">', unsafe_allow_html=True)
                    else:
                        st.markdown(f'<div style="width:100%; height:180px; background:#FDF8F5; display:flex; align-items:center; justify-content:center; color:#8B3E04; font-weight:bold; font-size:1.2rem; border-bottom: 1px solid #F0F0F0;">📜 纯文本分享</div>', unsafe_allow_html=True)
                    
                    st.button(post["title"], key=f"view_btn_{post['id']}", on_click=set_view_post, args=(post['id'],), use_container_width=True)
                        
                    st.markdown(f'''
                        <div style="display: flex; align-items: center; justify-content: space-between; font-size: 0.85rem; color: #777; padding: 0 15px 15px 15px;">
                            <div style="display: flex; align-items: center; gap: 8px;">{render_avatar(post['avatar'], '22px', '1rem')} <span style="font-weight:bold; color:#555;">{post["name"]}</span></div>
                            <div style="font-weight:bold; color:#E06C75;">❤️ {likes_count}</div>
                        </div>
                    </div>
                    ''', unsafe_allow_html=True)

    else:
        current_post = next((p for p in posts_data if p["id"] == st.session_state.view_post_id), None)
        
        if current_post is None:
            clear_view_post()
            st.rerun()
            
        st.markdown('<div class="back-btn">', unsafe_allow_html=True)
        st.button("返回上一页", on_click=clear_view_post)
        st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown(f'''
            <div class="detail-post-box">
                <h1 style="color:#222; font-weight:900; margin-bottom: 25px; text-align: left;">{current_post['title']}</h1>
                <div class="detail-author-row">
                    {render_avatar(current_post['avatar'], '60px', '2.2rem')}
                    <div>
                        <div style="font-weight:bold; font-size:1.2rem; color:#333;">{current_post['name']}</div>
                        <div style="color:#888; font-size:0.9rem;">{current_post['time']}</div>
                    </div>
                </div>
                <div class="detail-content">{current_post['content']}</div>
            </div>
        ''', unsafe_allow_html=True)
        
        if current_post.get("image"):
            st.markdown(f'<img src="{current_post["image"]}" class="detail-img">', unsafe_allow_html=True)

        if "liked_by" not in current_post: current_post["liked_by"] = []
        user_id = st.session_state.user_profile["id"]
        is_liked = user_id in current_post["liked_by"]
        
        col_like, col_space = st.columns([1.2, 8.8])
        with col_like:
            btn_label = f"❤️ {len(current_post['liked_by']) + current_post.get('likes', 0)}" if is_liked else f"🤍 {len(current_post['liked_by']) + current_post.get('likes', 0)}"
            
            st.markdown('<div class="icon-action-btn">', unsafe_allow_html=True)
            if st.button(btn_label, key="like_post_btn", type="primary" if is_liked else "secondary", use_container_width=True):
                if is_liked: current_post["liked_by"].remove(user_id)
                else: current_post["liked_by"].append(user_id)
                save_posts(posts_data)
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div style="margin-top: 30px; border-top: 1px solid #EAD8C3; padding-top: 20px;"><h3 style="color:#333; font-weight:800;">共 '+str(len(current_post.get('comments', [])))+' 条评论</h3></div>', unsafe_allow_html=True)
        
        for c_idx, c in enumerate(current_post.get("comments", [])):
            if "up_by" not in c: c["up_by"] = []
            if "down_by" not in c: c["down_by"] = []
            
            is_up = user_id in c["up_by"]
            is_down = user_id in c["down_by"]
            
            is_reply = "回复 <span" in c['content']
            margin_left = "52px" if is_reply else "0px"
            border_left = "3px solid #EEEEEE" if is_reply else "none"
            padding_left = "15px" if is_reply else "0px"
            avatar_size = "30px" if is_reply else "40px"
            time_padding = "68px" if is_reply else "55px"

            st.markdown(f'''
                <div style="display:flex; gap:12px; margin-bottom:-10px; margin-left:{margin_left}; border-left:{border_left}; padding-left:{padding_left};">
                    {render_avatar(c['avatar'], avatar_size, '1.3rem')}
                    <div style="flex:1;">
                        <div style="font-weight:bold; color:#555; font-size:0.95rem; margin-bottom:5px;">{c['name']}</div>
                        <div style="color:#333; font-size:1.05rem; padding-bottom:28px;">{c['content']}</div>
                    </div>
                </div>
            ''', unsafe_allow_html=True)
            
            btn_col1, btn_col2, btn_col3, btn_col4 = st.columns([7, 1, 1, 1.5])
            with btn_col1:
                st.markdown(f"<div style='font-size:0.8rem; color:#AAA; padding-top:5px; padding-left:{time_padding};'>{c['time']}</div>", unsafe_allow_html=True)
            with btn_col2:
                st.markdown('<div class="icon-action-btn">', unsafe_allow_html=True)
                if st.button(f"👍 {len(c['up_by']) + c.get('up', 0)}", key=f"up_{c['c_id']}", type="primary" if is_up else "secondary", use_container_width=True):
                    if is_up: c['up_by'].remove(user_id)
                    else: 
                        c['up_by'].append(user_id)
                        if is_down: c['down_by'].remove(user_id) 
                    save_posts(posts_data)
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)
            with btn_col3:
                st.markdown('<div class="icon-action-btn">', unsafe_allow_html=True)
                if st.button(f"👎 {len(c['down_by']) + c.get('down', 0)}", key=f"down_{c['c_id']}", type="primary" if is_down else "secondary", use_container_width=True):
                    if is_down: c['down_by'].remove(user_id)
                    else: 
                        c['down_by'].append(user_id)
                        if is_up: c['up_by'].remove(user_id)
                    save_posts(posts_data)
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)
            with btn_col4:
                st.markdown('<div class="icon-action-btn">', unsafe_allow_html=True)
                st.button("回复", key=f"reply_{c['c_id']}", on_click=set_reply, args=(c['name'],), use_container_width=True)
                st.markdown('</div>', unsafe_allow_html=True)
                
            st.markdown('<div style="border-bottom: 1px dashed #EEEEEE; margin-bottom: 15px; margin-top: 10px;"></div>', unsafe_allow_html=True)

        st.write("---")
        
        reply_to_name = st.session_state.reply_target
        if reply_to_name:
            col_rt1, col_rt2 = st.columns([8, 2])
            with col_rt1:
                st.markdown(f"<div style='color:#8B3E04; font-weight:bold; margin-bottom: 10px;'>正在回复 @{reply_to_name}</div>", unsafe_allow_html=True)
            with col_rt2:
                st.button("取消回复", on_click=clear_reply)
        else:
            st.markdown("##### 留下您的评论")

        with st.form("add_comment_form", clear_on_submit=True):
            placeholder_text = f"回复 @{reply_to_name}..." if reply_to_name else "写点什么吧..."
            c_text = st.text_input("评论内容...", max_chars=100, label_visibility="collapsed", placeholder=placeholder_text)
            st.markdown(f"<div style='font-size:0.85rem; color:#888; margin-bottom:10px;'>将以 <b>{st.session_state.user_profile['name']}</b> 的身份发布</div>", unsafe_allow_html=True)
            c_submit = st.form_submit_button("发送评论")
            if c_submit:
                if not c_text.strip():
                    st.error("评论内容不能为空哦！")
                else:
                    final_content = f"回复 <span style='color:#5C1D16; font-weight:bold;'>@{reply_to_name}</span>：{c_text.strip()}" if reply_to_name else c_text.strip()
                    
                    new_comment = {
                        "c_id": "comment_" + str(os.urandom(4).hex()),
                        "name": st.session_state.user_profile["name"],
                        "avatar": st.session_state.user_profile["avatar"],
                        "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
                        "content": final_content,
                        "up_by": [],
                        "down_by": []
                    }
                    if "comments" not in current_post:
                        current_post["comments"] = []
                    current_post["comments"].append(new_comment)
                    save_posts(posts_data)
                    
                    st.session_state.reply_target = None
                    st.rerun()