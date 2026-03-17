import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import requests
import base64
import os
from streamlit_echarts import st_echarts, Map

# 1. 网页全局配置
st.set_page_config(page_title="华夏遗珍 | 数智交互平台", layout="wide", initial_sidebar_state="collapsed")

# ================= 核心跳转拦截器 (跨页面通信) =================
# 捕获 URL 参数，实现跨页面的无缝跳转
if "nav" in st.query_params:
    target_nav = st.query_params["nav"]
    target_site = st.query_params.get("site", None)
    if target_nav == "baike":
        st.session_state.current_page = "遗珍百科"
        st.session_state.detail_item = target_site
    st.query_params.clear() 

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

# 加入了第五张图的路径处理
img1 = get_image_base64("image/The_Great_Wall_of_China.jpg", "https://images.unsplash.com/photo-1508804185872-d7badad00f7d?w=1200&q=80")
img2 = get_image_base64("image/gugong.jpg", "https://images.unsplash.com/photo-1584646098378-0874589d79b1?w=1200&q=80")
img3 = get_image_base64("image/West_Lake.jpg", "https://images.unsplash.com/photo-1626014903706-5b4372e90f62?w=1200&q=80")
img4 = get_image_base64("image/TerracotaArmy.jpg", "https://images.unsplash.com/photo-1597953600326-9fba8e1a1293?w=1200&q=80")
img5 = get_image_base64("image/Potala_Palace.jpg", "https://images.unsplash.com/photo-1583208754160-7ea00f1c305a?w=1200&q=80") # 第五张图

# ================= 维基百科 API 实时接口 =================
@st.cache_data(ttl=86400) 
def fetch_wikipedia_summary(title):
    # 使用 redirects=1 解决维基百科重定向问题
    url = f"https://zh.wikipedia.org/w/api.php?action=query&prop=extracts&exintro&explaintext&titles={title}&redirects=1&format=json&utf8=1"
    try:
        res = requests.get(url, timeout=5).json()
        pages = res.get("query", {}).get("pages", {})
        for pid, pdata in pages.items():
            if pid != '-1':
                extract = pdata.get('extract', '')
                if extract:
                    return extract
    except Exception:
        pass
    return None

# 2. 深度美化 CSS (无 Emoji，极致专业)
st.markdown("""
    <style>
    [data-testid="collapsedControl"] {display: none;}
    [data-testid="stSidebar"] {display: none;}
    .block-container { padding-top: 1rem !important; padding-bottom: 1rem !important; max-width: 95% !important;}
    
    div.stButton > button {
        width: 100%; border: none; background-color: transparent; color: #5C1D16; 
        font-size: 1.25rem; font-weight: 800; border-bottom: 3px solid transparent; border-radius: 0; padding: 12px 0;
    }
    div.stButton > button:hover { border-bottom: 3px solid #8B3E04; color: #8B3E04; background-color: #FDF8F5;}
    
    .main-title {font-size: 2.6rem; font-weight: 900; color: #5C1D16; margin-bottom: 0.5rem; letter-spacing: 2px;}
    .sub-title {font-size: 1.3rem; color: #8C6A4F; margin-bottom: 1.5rem; border-bottom: 2px solid #EAD8C3; padding-bottom: 10px;}
    
    /* 压扁指标卡片 */
    .metric-card {background-color: #FAFAFA; padding: 15px 25px; border-radius: 8px; border-left: 5px solid #8B3E04; box-shadow: 0px 4px 10px rgba(0,0,0,0.05);}
    .metric-card h2 {color: #8B3E04; margin-top: 0; margin-bottom: 5px; font-size: 2.4rem; font-weight: bold;}
    .metric-card p {color: #555555; margin-bottom: 0; font-size: 1.1rem; font-weight: 500;}
    
    .detail-header {text-align: center; margin-bottom: 20px;}
    .detail-title {font-size: 2.5rem; color: #5C1D16; font-weight: 900;}
    .detail-tag {display: inline-block; background-color: #FDF8F5; color: #8B3E04; padding: 5px 15px; border-radius: 20px; font-size: 1rem; font-weight: 600; margin: 5px; border: 1px solid #EAD8C3;}
    .section-title {color: #8B3E04; font-size: 1.5rem; font-weight: bold; margin-top: 25px; border-left: 4px solid #C68244; padding-left: 10px;}
    .detail-text {font-size: 1.15rem; color: #444; line-height: 1.8; text-align: justify; margin-top: 10px;}
    
    /* 居中大号表格 */
    .custom-table { width: 100%; border-collapse: collapse; font-size: 1.2rem; text-align: center; margin-bottom: 20px;}
    .custom-table th { background-color: #8B3E04; color: white; padding: 15px; text-align: center; font-weight: 600;}
    .custom-table td { padding: 15px; border-bottom: 1px solid #EAD8C3; color: #333;}
    .custom-table tr:hover { background-color: #FDF8F5; }
    
    /* 大屏经典名录样式与可点击链接 */
    .list-category {color: #A0522D; font-size: 1.4rem; margin-top: 20px; margin-bottom: 10px; font-weight: bold; border-bottom: 1px solid #EAD8C3; padding-bottom: 5px;}
    .map-link {font-size: 1.15rem; color: #333333; line-height: 2.0; margin-left: 10px; text-decoration: none; display: block; transition: all 0.2s;}
    .map-link:hover {color: #8B3E04; font-weight: bold; padding-left: 5px;}
    .map-link::before {content: "• "; color: #C68244;}
    </style>
""", unsafe_allow_html=True)

# 3. 核心大一统数据库 (60项统一名称)
heritage_data = {
    "北京市": {"文化": ["长城", "明清故宫", "周口店北京人遗址", "颐和园", "天坛", "明清皇家陵寝", "北京中轴线", "大运河"], "自然": [], "双重": []},
    "天津市": {"文化": ["大运河"], "自然": [], "双重": []},
    "河北省": {"文化": ["长城", "承德避暑山庄及其周围寺庙", "明清皇家陵寝", "大运河"], "自然": ["中国黄（渤）海候鸟栖息地"], "双重": []},
    "山西省": {"文化": ["平遥古城", "云冈石窟", "五台山"], "自然": [], "双重": []},
    "内蒙古自治区": {"文化": ["元上都遗址"], "自然": ["巴丹吉林沙漠"], "双重": []},
    "辽宁省": {"文化": ["明清故宫", "明清皇家陵寝", "高句丽王城、王陵及贵族墓葬"], "自然": ["中国黄（渤）海候鸟栖息地"], "双重": []},
    "吉林省": {"文化": ["高句丽王城、王陵及贵族墓葬"], "自然": [], "双重": []},
    "上海市": {"文化": [], "自然": ["中国黄（渤）海候鸟栖息地"], "双重": []},
    "江苏省": {"文化": ["苏州古典园林", "明清皇家陵寝", "大运河"], "自然": ["中国黄（渤）海候鸟栖息地"], "双重": []},
    "浙江省": {"文化": ["杭州西湖文化景观", "良渚古城遗址", "大运河"], "自然": ["中国丹霞"], "双重": []},
    "安徽省": {"文化": ["皖南古村落—西递、宏村", "大运河"], "自然": [], "双重": ["黄山"]},
    "福建省": {"文化": ["福建土楼", "鼓浪屿：历史国际社区", "泉州：宋元中国的世界海洋商贸中心"], "自然": ["中国丹霞"], "双重": ["武夷山"]},
    "江西省": {"文化": ["庐山国家级风景名胜区"], "自然": ["三清山国家级风景名胜区", "中国丹霞"], "双重": ["武夷山"]},
    "山东省": {"文化": ["曲阜孔庙、孔林和孔府", "大运河"], "自然": ["中国黄（渤）海候鸟栖息地"], "双重": ["泰山"]},
    "河南省": {"文化": ["龙门石窟", "殷墟", "登封“天地之中”历史建筑群", "大运河", "丝绸之路：长安-天山廊道的路网"], "自然": [], "双重": []},
    "湖北省": {"文化": ["武当山古建筑群", "明清皇家陵寝", "土司遗址"], "自然": ["湖北神农架"], "双重": []},
    "湖南省": {"文化": ["土司遗址"], "自然": ["武陵源风景名胜区", "中国丹霞"], "双重": []},
    "广东省": {"文化": ["开平碉楼与村落"], "自然": ["中国丹霞"], "双重": []},
    "广西壮族自治区": {"文化": ["左江花山岩画文化景观"], "自然": ["中国南方喀斯特"], "双重": []},
    "重庆市": {"文化": ["大足石刻"], "自然": ["中国南方喀斯特", "湖北神农架"], "双重": []},
    "四川省": {"文化": ["青城山—都江堰"], "自然": ["九寨沟风景名胜区", "黄龙风景名胜区", "四川大熊猫栖息地"], "双重": ["峨眉山—乐山大佛"]},
    "贵州省": {"文化": ["土司遗址"], "自然": ["梵净山", "中国南方喀斯特", "中国丹霞"], "双重": []},
    "云南省": {"文化": ["丽江古城", "红河哈尼梯田文化景观", "普洱景迈山古茶林文化景观"], "自然": ["云南三江并流保护区", "澄江化石地", "中国南方喀斯特"], "双重": []},
    "西藏自治区": {"文化": ["拉萨布达拉宫历史建筑群"], "自然": [], "双重": []},
    "陕西省": {"文化": ["秦始皇陵及兵马俑坑", "丝绸之路：长安-天山廊道的路网"], "自然": [], "双重": []},
    "甘肃省": {"文化": ["莫高窟", "长城", "丝绸之路：长安-天山廊道的路网"], "自然": [], "双重": []},
    "青海省": {"文化": [], "自然": ["青海可可西里"], "双重": []},
    "宁夏回族自治区": {"文化": ["西夏陵"], "自然": [], "双重": []},
    "新疆维吾尔自治区": {"文化": ["丝绸之路：长安-天山廊道的路网"], "自然": ["新疆天山"], "双重": []},
    "澳门特别行政区": {"文化": ["澳门历史城区"], "自然": [], "双重": []}
}

# 提取用于百科检索的扁平化列表
all_heritage_list = []
seen_names = set()
for prov, categories in heritage_data.items():
    for cat_name, items in categories.items():
        for item_name in items:
            # 保证百科列表里同名遗产只出现一次
            if item_name not in seen_names:
                cat_full = "世界文化遗产" if cat_name == "文化" else "世界自然遗产" if cat_name == "自然" else "文化与自然双重遗产"
                all_heritage_list.append({"name": item_name, "province": prov, "category": cat_full})
                seen_names.add(item_name)

# ================= 路由与状态管理 =================
if 'current_page' not in st.session_state:
    st.session_state.current_page = "首页视界"
if 'detail_item' not in st.session_state:
    st.session_state.detail_item = None

# ================= 顶部全局导航栏 =================
# 标题靠左绝对对齐，去除了Emoji
st.markdown('''
    <div style="background-color: #5C1D16; padding: 15px 25px; color: #EAD8C3; font-size: 1.6rem; font-weight: bold; border-radius: 8px 8px 0 0; margin-bottom: 10px; text-align: left; letter-spacing: 2px;">
        华夏遗珍 | 中国世界遗产数智交互平台
    </div>
''', unsafe_allow_html=True)

col1, col2, col3, col4 = st.columns(4)
with col1: 
    if st.button("首页视界", use_container_width=True): st.session_state.current_page = "首页视界"; st.session_state.detail_item = None
with col2: 
    if st.button("数据大屏", use_container_width=True): st.session_state.current_page = "数据大屏"; st.session_state.detail_item = None
with col3: 
    if st.button("遗珍百科", use_container_width=True): st.session_state.current_page = "遗珍百科"; st.session_state.detail_item = None
with col4: 
    if st.button("AI 智游", use_container_width=True): st.session_state.current_page = "AI 智游"; st.session_state.detail_item = None

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
        /* 故宫沉红柔和渐变蒙版 */
        .overlay { position: absolute; top: 0; left: 0; width: 100%; height: 100%; background: linear-gradient(to right, rgba(92,29,22,0.85) 0%, rgba(92,29,22,0.4) 50%, rgba(0,0,0,0) 100%); }
        .thumbnails { position: absolute; left: 30px; top: 50%; transform: translateY(-50%); display: flex; flex-direction: column; gap: 12px; z-index: 10; }
        .thumb-wrapper { position: relative; width: 65px; height: 65px; border-radius: 50%; cursor: pointer; border: 3px solid rgba(255,255,255,0.5); overflow: hidden; transition: all 0.3s ease; box-shadow: 0 4px 10px rgba(0,0,0,0.5); }
        .thumb-wrapper:hover, .thumb-wrapper.active { border-color: #E6B885; transform: scale(1.15); }
        .thumb-wrapper img { width: 100%; height: 100%; object-fit: cover; }
        
        .text-content { position: absolute; left: 140px; bottom: 50px; z-index: 10; width: 700px; display: flex; justify-content: space-between; align-items: flex-end; }
        .text-info { max-width: 500px; }
        .text-info h1 { font-size: 3rem; margin: 0 0 10px 0; color: #E6B885; text-shadow: 2px 2px 4px rgba(0,0,0,0.8); }
        .text-info p { font-size: 1.15rem; margin: 0; line-height: 1.6; text-shadow: 1px 1px 3px rgba(0,0,0,0.8); color: #EEEEEE; }
        
        /* 白字透明方框按钮 */
        .btn-square { display: inline-block; padding: 10px 20px; border: 2px solid #FFFFFF; background-color: transparent; color: #FFFFFF; text-decoration: none; font-size: 1.1rem; font-weight: bold; cursor: pointer; transition: all 0.3s; margin-bottom: 5px; border-radius: 2px; letter-spacing: 2px;}
        .btn-square:hover { background-color: #FFFFFF; color: #5C1D16; }
    </style>
    </head>
    <body>
    <div class="hero-container">
        <img id="main-bg" class="bg-image" src="IMG_SRC_1">
        <div class="overlay"></div>
        <div class="thumbnails">
            <div class="thumb-wrapper active" onclick="changeSlide(0, this)"><img src="IMG_SRC_1"></div>
            <div class="thumb-wrapper" onclick="changeSlide(1, this)"><img src="IMG_SRC_2"></div>
            <div class="thumb-wrapper" onclick="changeSlide(2, this)"><img src="IMG_SRC_3"></div>
            <div class="thumb-wrapper" onclick="changeSlide(3, this)"><img src="IMG_SRC_4"></div>
            <div class="thumb-wrapper" onclick="changeSlide(4, this)"><img src="IMG_SRC_5"></div>
        </div>
        <div class="text-content">
            <div class="text-info">
                <h1 id="main-title">长城</h1>
                <p id="main-desc">世界文化遗产，中华民族的精神象征与智慧结晶，跨越千年的防御工程奇迹。</p>
            </div>
            <a id="jump-btn" href="javascript:void(0);" onclick="goToDetail()" class="btn-square">查看详情</a>
        </div>
    </div>
    <script>
        const slides = [
            { img: 'IMG_SRC_1', title: '长城', desc: '世界文化遗产，中华民族的精神象征与智慧结晶，跨越千年的防御工程奇迹。' },
            { img: 'IMG_SRC_2', title: '明清故宫', desc: '世界文化遗产，明清两代皇家宫殿，中国古代宫廷建筑之精华，无与伦比的历史杰作。' },
            { img: 'IMG_SRC_3', title: '杭州西湖文化景观', desc: '世界文化景观遗产，秀丽的自然风光与深厚的文化底蕴完美融合，江南水乡的代表。' },
            { img: 'IMG_SRC_4', title: '秦始皇陵及兵马俑坑', desc: '世界文化遗产，被誉为“世界第八大奇迹”，展现了秦代高超的雕塑艺术与大一统气象。' },
            { img: 'IMG_SRC_5', title: '拉萨布达拉宫历史建筑群', desc: '世界文化遗产，世界上海拔最高、集宫殿、城堡和寺院于一体的宏伟建筑。' }
        ];
        let currentSlideIndex = 0;
        
        function changeSlide(index, element) {
            currentSlideIndex = index;
            const bg = document.getElementById('main-bg');
            const title = document.getElementById('main-title');
            const desc = document.getElementById('main-desc');
            document.querySelectorAll('.thumb-wrapper').forEach(el => el.classList.remove('active'));
            element.classList.add('active');
            bg.style.opacity = 0;
            setTimeout(() => { bg.src = slides[index].img; title.innerText = slides[index].title; desc.innerText = slides[index].desc; bg.style.opacity = 1; }, 400); 
        }
        
        // 核心跳转逻辑修改，直接操作父窗口 URL
        function goToDetail() {
            const currentTitle = slides[currentSlideIndex].title;
            window.parent.location.search = "?nav=baike&site=" + encodeURIComponent(currentTitle);
        }
    </script>
    </body>
    </html>
    """
    final_html = html_template.replace("IMG_SRC_1", img1).replace("IMG_SRC_2", img2).replace("IMG_SRC_3", img3).replace("IMG_SRC_4", img4).replace("IMG_SRC_5", img5)
    components.html(final_html, height=620)

# ================= 页面二：大屏 =================
elif st.session_state.current_page == "数据大屏":
    st.markdown('<h1 class="main-title">中国世界遗产分布大屏</h1>', unsafe_allow_html=True)
    st.markdown('<h3 class="sub-title">宏观数据统计与省级名录动态查询</h3>', unsafe_allow_html=True)

    col1, col2, col3, col4 = st.columns(4)
    with col1: st.markdown('<div class="metric-card"><h2>60 项</h2><p>中国世界遗产总数</p></div>', unsafe_allow_html=True)
    with col2: st.markdown('<div class="metric-card"><h2>41 项</h2><p>世界文化遗产</p></div>', unsafe_allow_html=True)
    with col3: st.markdown('<div class="metric-card"><h2>15 项</h2><p>世界自然遗产</p></div>', unsafe_allow_html=True)
    with col4: st.markdown('<div class="metric-card"><h2>4 项</h2><p>文化与自然双重遗产</p></div>', unsafe_allow_html=True)

    st.write("---")

    @st.cache_data
    def load_china_map():
        url = "https://geo.datav.aliyun.com/areas_v3/bound/100000_full.json"
        return requests.get(url).json()

    map_obj = Map("china", load_china_map())
    map_col, list_col = st.columns([1.2, 1])
    all_provinces = ["北京市", "天津市", "河北省", "山西省", "内蒙古自治区", "辽宁省", "吉林省", "黑龙江省", "上海市", "江苏省", "浙江省", "安徽省", "福建省", "江西省", "山东省", "河南省", "湖北省", "湖南省", "广东省", "广西壮族自治区", "海南省", "重庆市", "四川省", "贵州省", "云南省", "西藏自治区", "陕西省", "甘肃省", "青海省", "宁夏回族自治区", "新疆维吾尔自治区", "台湾省", "香港特别行政区", "澳门特别行政区"]

    with map_col:
        st.markdown('<h3 style="color:#5C1D16;">交互地图</h3>', unsafe_allow_html=True) # 删除了冗余提示
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
            "visualMap": { "min": 0, "max": 8, "text": ["遗产多", "无遗产"], "realtime": False, "calculable": True, "inRange": {"color": ["#FDF8F5", "#E6BA89", "#C17942", "#8B3E04"]}, "textStyle": {"color": "#666666"} },
            "series": [{ "name": "遗产数量", "type": "map", "mapType": "china", "roam": True, "zoom": 1.3, "label": {"show": False}, "itemStyle": {"areaColor": "#FDF8F5", "borderColor": "#CCCCCC"}, "emphasis": {"label": {"show": True, "color": "#FFF", "fontWeight": "bold"}, "itemStyle": {"areaColor": "#5C2600"}}, "data": map_data }]
        }
        clicked_data = st_echarts(map_options, map=map_obj, events={"click": "function(params) { return params.name; }"}, height="600px", key="china_map")

    with list_col:
        st.markdown('<h3 style="color:#5C1D16;">地方遗珍名录</h3>', unsafe_allow_html=True)
        province_name = None
        if clicked_data:
            clicked_str = str(clicked_data)
            for prov in all_provinces:
                if prov in clicked_str:
                    province_name = prov
                    break
            
        if not province_name:
            st.info("请在左侧地图点击高亮的省份，查看具体的遗产名录。你可以使用鼠标滚轮放大或缩小地图区域。")
        elif province_name not in heritage_data or (len(heritage_data[province_name]["文化"]) + len(heritage_data[province_name]["自然"]) + len(heritage_data[province_name]["双重"]) == 0):
            st.markdown(f'<h3 class="province-title">{province_name}</h3>', unsafe_allow_html=True)
            st.info("该省份暂未列入世界遗产名录，期待未来的发现与传承！")
        else:
            st.markdown(f'<h3 class="province-title">{province_name}</h3>', unsafe_allow_html=True)
            data = heritage_data[province_name]
            
            # 🔥 恢复了经典的排版，并且加入了超级跳转链接 (直接点击名字跳转百科)
            if data["文化"]:
                st.markdown('<div class="list-category">世界文化遗产</div>', unsafe_allow_html=True)
                for item in data["文化"]: 
                    st.markdown(f'<a href="?nav=baike&site={item}" target="_parent" class="map-link">{item}</a>', unsafe_allow_html=True)
            if data["自然"]:
                st.markdown('<div class="list-category">世界自然遗产</div>', unsafe_allow_html=True)
                for item in data["自然"]: 
                    st.markdown(f'<a href="?nav=baike&site={item}" target="_parent" class="map-link">{item}</a>', unsafe_allow_html=True)
            if data["双重"]:
                st.markdown('<div class="list-category">世界文化与自然双重遗产</div>', unsafe_allow_html=True)
                for item in data["双重"]: 
                    st.markdown(f'<a href="?nav=baike&site={item}" target="_parent" class="map-link">{item}</a>', unsafe_allow_html=True)

# ================= 页面三：百科 =================
elif st.session_state.current_page == "遗珍百科":
    
    if st.session_state.detail_item:
        site_name = st.session_state.detail_item
        base_info = next((item for item in all_heritage_list if item["name"] == site_name), None)
        
        if st.button("返回清单检索"):
            st.session_state.detail_item = None
            st.rerun()
            
        st.markdown(f'''
            <div class="detail-header">
                <div class="detail-title">{site_name}</div>
                <div style="margin-top:10px;">
                    <span class="detail-tag">所在地区：{base_info["province"] if base_info else "跨省区/未获取"}</span>
                    <span class="detail-tag">遗产类别：{base_info["category"] if base_info else "世界文化遗产"}</span>
                </div>
            </div>
        ''', unsafe_allow_html=True)
        
        # 实时调取维基百科接口
        wiki_text = fetch_wikipedia_summary(site_name)
        if wiki_text:
            st.markdown(f'<div class="section-title">权威摘要文献</div><div class="detail-text">{wiki_text}</div>', unsafe_allow_html=True)
        else:
            st.warning("网络原因或条目未完全匹配，无法从权威接口获取该遗产的信息。")
            st.markdown('<div class="detail-text" style="text-align:center;">想要了解深度的导游级讲解，您可以前往【AI 智游】模块提问！</div>', unsafe_allow_html=True)

    else:
        st.markdown('<h1 class="main-title" style="font-size: 2.4rem;">国家级文化遗产名录检索</h1>', unsafe_allow_html=True)
        st.markdown('<div class="sub-title" style="margin-bottom: 20px;">全量60项独立数据已收录。支持按地区、类别、关键词查询。</div>', unsafe_allow_html=True)
        
        f_col1, f_col2, f_col3 = st.columns(3)
        with f_col1: search_prov = st.selectbox("所在地区", ["全部"] + list(heritage_data.keys()))
        with f_col2: search_cat = st.selectbox("遗产类别", ["全部", "世界文化遗产", "世界自然遗产", "文化与自然双重遗产"])
        with f_col3: search_kw = st.text_input("输入关键词检索", "")

        filtered_df = []
        for idx, item in enumerate(all_heritage_list):
            if search_prov != "全部" and item["province"] != search_prov: continue
            if search_cat != "全部" and item["category"] != search_cat: continue
            if search_kw and search_kw.lower() not in item["name"].lower(): continue
            filtered_df.append({"序号": idx+1, "名称": item["name"], "类别": item["category"], "所在地区": item["province"]})
            
        if not filtered_df:
            st.warning("未找到匹配的遗产，请尝试放宽筛选条件。")
        else:
            df = pd.DataFrame(filtered_df)
            html_table = df.to_html(index=False, classes='custom-table', escape=False)
            html_table = html_table.replace('<th>序号</th>', '<th style="width: 10%;">序号</th>')
            st.markdown(html_table, unsafe_allow_html=True)
            
            st.write("---")
            selected_site = st.selectbox("选择你要查看的遗产名称，点击下方按钮查阅详细档案：", [row["名称"] for row in filtered_df])
            if st.button("进入详情页", type="primary"):
                st.session_state.detail_item = selected_site
                st.rerun()

# ================= 页面四：AI 大模型 =================
elif st.session_state.current_page == "AI 智游":
    st.markdown('<h1 class="main-title">AI：智游遗迹</h1>', unsafe_allow_html=True)
    st.markdown('<h3 class="sub-title">您的专属世界文化遗产智能导游。</h3>', unsafe_allow_html=True)
    st.info("AI 视觉大模型接口接入准备中... 敬请期待！")