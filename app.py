import streamlit as st
import streamlit.components.v1 as components
import requests
import base64
import os
from streamlit_echarts import st_echarts, Map

# 1. 网页全局配置
st.set_page_config(page_title="华夏遗珍 | 数智交互平台", layout="wide", initial_sidebar_state="expanded")

# ================= 核心黑客科技：本地图片转 Base64 引擎 =================
@st.cache_data
def get_image_base64(img_path, fallback_url):
    """把本地图片转化为网页可直接读取的 base64 编码，若本地没有则用网络图兜底"""
    try:
        if os.path.exists(img_path):
            with open(img_path, "rb") as img_file:
                return "data:image/jpeg;base64," + base64.b64encode(img_file.read()).decode('utf-8')
    except Exception:
        pass
    return fallback_url

# 读取你准备好的本地图片 (第四张先用长城代替，记得之后改路径哦)
img1 = get_image_base64("image/The_Great_Wall_of_China.jpg", "https://images.unsplash.com/photo-1508804185872-d7badad00f7d?w=1200&q=80")
img2 = get_image_base64("image/gugong.jpg", "https://images.unsplash.com/photo-1584646098378-0874589d79b1?w=1200&q=80")
img3 = get_image_base64("image/West_Lake.jpg", "https://images.unsplash.com/photo-1626014903706-5b4372e90f62?w=1200&q=80")
img4 = get_image_base64("image/The_Great_Wall_of_China.jpg", "https://images.unsplash.com/photo-1597953600326-9fba8e1a1293?w=1200&q=80")

# 2. 深度美化 CSS：压缩顶部留白、美化标题、放大侧边栏
st.markdown("""
    <style>
    /* 强行压缩顶部自带的巨大留白 */
    .block-container { padding-top: 1.5rem !important; padding-bottom: 1rem !important; }
    
    /* 侧边栏整体与字体美化：更大、更清晰 */
    [data-testid="stSidebar"] { background-color: #FDF8F5; border-right: 1px solid #EAEAEA; }
    div[role="radiogroup"] > label { margin-bottom: 12px !important; cursor: pointer; }
    div[role="radiogroup"] p { font-size: 1.35rem !important; font-weight: 600 !important; color: #5C2600 !important; letter-spacing: 1px; }
    
    /* 大标题：使用深邃的“故宫沉红”，增加轻微阴影更显厚重 */
    .main-title {font-size: 2.8rem; font-weight: 900; color: #5C1D16; margin-bottom: 0.5rem; letter-spacing: 3px; text-shadow: 1px 1px 2px rgba(0,0,0,0.05);}
    /* 副标题：使用典雅的“金石青铜”色，增加质感 */
    .sub-title {font-size: 1.35rem; color: #8C6A4F; margin-bottom: 1.5rem; font-weight: 500; border-bottom: 1px solid #EAD8C3; padding-bottom: 15px; letter-spacing: 1px;}
    
    /* 指标卡片 */
    .metric-card {background-color: #FAFAFA; padding: 25px; border-radius: 8px; border: 1px solid #EEEEEE; border-left: 5px solid #8B3E04; box-shadow: 0px 4px 10px rgba(0,0,0,0.05);}
    .metric-card h2 {color: #8B3E04; margin-top: 0; font-size: 2.6rem; font-weight: bold;}
    .metric-card p {color: #555555; margin-bottom: 0; font-size: 1.1rem; font-weight: 500;}
    
    /* 名录区 */
    .province-title {color: #8B3E04; border-bottom: 2px solid #C68244; padding-bottom: 10px; font-size: 2rem;}
    .list-category {color: #A0522D; font-size: 1.3rem; margin-top: 15px; margin-bottom: 10px; font-weight: 600;}
    .list-item {font-size: 1.1rem; color: #333333; line-height: 1.8; margin-left: 10px;}
    .list-item::before {content: "✦ "; color: #C68244;}
    </style>
""", unsafe_allow_html=True)

# 3. 核心数据库 (截至 2025 年 7 月)
heritage_data = {
    "北京市": {"文化": ["周口店北京人遗址", "北京皇家园林—颐和园", "北京皇家祭坛—天坛", "北京中轴线", "长城 (八达岭)", "北京及沈阳的明清皇家宫殿 (北京故宫)", "明清皇家陵寝 (明十三陵)", "大运河 (通惠河)"], "自然": [], "双重": []},
    "天津市": {"文化": ["大运河 (北运河)"], "自然": [], "双重": []},
    "河北省": {"文化": ["承德避暑山庄及其周围寺庙", "长城 (山海关)", "明清皇家陵寝 (清东陵、清西陵)", "大运河 (南运河)"], "自然": ["中国黄（渤）海候鸟栖息地 (南大港)"], "双重": []},
    "山西省": {"文化": ["平遥古城", "云冈石窟", "五台山"], "自然": [], "双重": []},
    "内蒙古自治区": {"文化": ["元上都遗址"], "自然": ["巴丹吉林沙漠"], "双重": []},
    "辽宁省": {"文化": ["北京及沈阳的明清皇家宫殿 (沈阳故宫)", "明清皇家陵寝 (盛京三陵)", "高句丽王城、王陵及贵族墓葬 (五女山城)"], "自然": ["中国黄（渤）海候鸟栖息地 (大洋河-二道沟、九头山-蛇岛)"], "双重": []},
    "吉林省": {"文化": ["高句丽王城、王陵及贵族墓葬 (国内城、丸都山城、王陵及贵族墓葬)"], "自然": [], "双重": []},
    "上海市": {"文化": [], "自然": ["中国黄（渤）海候鸟栖息地 (崇明东滩)"], "双重": []},
    "江苏省": {"文化": ["苏州古典园林", "明清皇家陵寝 (明孝陵)", "大运河 (中运河、淮扬运河、江南运河)"], "自然": ["中国黄（渤）海候鸟栖息地 (盐城南部、盐城北部)"], "双重": []},
    "浙江省": {"文化": ["杭州西湖文化景观", "良渚古城遗址", "大运河 (江南运河、浙东运河)"], "自然": ["中国丹霞 (江郎山)"], "双重": []},
    "安徽省": {"文化": ["皖南古村落—西递、宏村", "大运河 (通济渠)"], "自然": [], "双重": ["黄山"]},
    "福建省": {"文化": ["福建土楼", "鼓浪屿：国际历史社区", "泉州：宋元中国的世界海洋商贸中心"], "自然": ["中国丹霞 (泰宁)"], "双重": ["武夷山 (主体)"]},
    "江西省": {"文化": ["庐山国家级风景名胜区"], "自然": ["三清山国家级风景名胜区", "中国丹霞 (龙虎山)"], "双重": ["武夷山 (江西武夷山)"]},
    "山东省": {"文化": ["曲阜孔庙、孔林和孔府", "大运河 (南运河、会通河、中运河)"], "自然": ["中国黄（渤）海候鸟栖息地 (黄河口-大汶流)"], "双重": ["泰山"]},
    "河南省": {"文化": ["龙门石窟", "殷墟", "登封“天地之中”历史建筑群", "大运河 (永济渠、通济渠)", "丝绸之路 (汉魏洛阳城遗址等)"], "自然": [], "双重": []},
    "湖北省": {"文化": ["武当山古建筑群", "明清皇家陵寝 (明显陵)", "土司遗址 (唐崖)"], "自然": ["湖北神农架 (主体)"], "双重": []},
    "湖南省": {"文化": ["土司遗址 (老司城)"], "自然": ["武陵源风景名胜区", "中国丹霞 (崀山)"], "双重": []},
    "广东省": {"文化": ["开平碉楼与村落"], "自然": ["中国丹霞 (丹霞山)"], "双重": []},
    "广西壮族自治区": {"文化": ["左江花山岩画文化景观"], "自然": ["中国南方喀斯特 (桂林、环江)"], "双重": []},
    "重庆市": {"文化": ["大足石刻"], "自然": ["中国南方喀斯特 (武隆、金佛山)", "湖北神农架 (重庆五里坡)"], "双重": []},
    "四川省": {"文化": ["青城山—都江堰"], "自然": ["九寨沟风景名胜区", "黄龙风景名胜区", "四川大熊猫栖息地"], "双重": ["峨眉山—乐山大佛"]},
    "贵州省": {"文化": ["土司遗址 (海龙屯)"], "自然": ["梵净山", "中国南方喀斯特 (荔波、施秉)", "中国丹霞 (赤水)"], "双重": []},
    "云南省": {"文化": ["丽江古城", "红河哈尼梯田文化景观", "普洱景迈山古茶林文化景观"], "自然": ["云南三江并流保护区", "澄江化石地", "中国南方喀斯特 (石林)"], "双重": []},
    "西藏自治区": {"文化": ["拉萨布达拉宫历史建筑群"], "自然": [], "双重": []},
    "陕西省": {"文化": ["秦始皇陵及兵马俑坑", "丝绸之路 (汉长安城未央宫遗址等)"], "自然": [], "双重": []},
    "甘肃省": {"文化": ["莫高窟", "长城 (嘉峪关)", "丝绸之路 (锁阳城遗址等)"], "自然": [], "双重": []},
    "青海省": {"文化": [], "自然": ["青海可可西里"], "双重": []},
    "宁夏回族自治区": {"文化": ["西夏陵"], "自然": [], "双重": []},
    "新疆维吾尔自治区": {"文化": ["丝绸之路 (高昌故城等)"], "自然": ["新疆天山"], "双重": []},
    "澳门特别行政区": {"文化": ["澳门历史城区"], "自然": [], "双重": []}
}

# ================= 极简高级侧边栏导航 =================
# 去掉 emoji，显得更加正式专业
st.sidebar.markdown('<h2 style="color:#5C1D16; margin-bottom: 20px;">系统导航</h2>', unsafe_allow_html=True)
page = st.sidebar.radio(
    "",
    ["遗珍视界", "遗产分布图", "AI：智游遗迹"]
)

st.sidebar.markdown("<br><br><br><hr>", unsafe_allow_html=True)
st.sidebar.write("平台版本: V2.0 (多模态交互版)")

# ================= 页面一：首页 (本地图文轮播) =================
if page == "遗珍视界":
    st.markdown('<h1 class="main-title">华夏遗珍：中国世界遗产数智交互平台</h1>', unsafe_allow_html=True)
    st.markdown('<h3 class="sub-title">让千年文化遗产在数字时代焕发新生，触摸历史的温度。</h3>', unsafe_allow_html=True)

    # 用 Python 的 replace 方法把我们解析的本地图片注入到 HTML 中
    html_template = """
    <!DOCTYPE html>
    <html>
    <head>
    <style>
        body { margin: 0; padding: 0; font-family: sans-serif; }
        .hero-container {
            position: relative; width: 100%; height: 550px; border-radius: 12px; overflow: hidden;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        }
        .bg-image {
            width: 100%; height: 100%; object-fit: cover;
            transition: opacity 0.6s ease-in-out; opacity: 1;
        }
        .overlay {
            position: absolute; top: 0; left: 0; width: 100%; height: 100%;
            background: linear-gradient(to right, rgba(0,0,0,0.85) 0%, rgba(0,0,0,0.4) 40%, rgba(0,0,0,0) 100%);
        }
        .thumbnails {
            position: absolute; left: 30px; top: 50%; transform: translateY(-50%);
            display: flex; flex-direction: column; gap: 15px; z-index: 10;
        }
        .thumb-wrapper {
            position: relative; width: 70px; height: 70px; border-radius: 50%;
            cursor: pointer; border: 3px solid rgba(255,255,255,0.5); overflow: hidden;
            transition: all 0.3s ease; box-shadow: 0 4px 10px rgba(0,0,0,0.5);
        }
        .thumb-wrapper:hover, .thumb-wrapper.active {
            border-color: #E6B885; transform: scale(1.15);
        }
        .thumb-wrapper img { width: 100%; height: 100%; object-fit: cover; }
        .text-content {
            position: absolute; left: 140px; bottom: 60px; color: white; z-index: 10; max-width: 600px;
        }
        .text-content h1 { font-size: 2.5rem; margin: 0 0 10px 0; color: #E6B885; text-shadow: 2px 2px 4px rgba(0,0,0,0.8); }
        .text-content p { font-size: 1.1rem; margin: 0; line-height: 1.5; text-shadow: 1px 1px 3px rgba(0,0,0,0.8); color: #EEEEEE; }
    </style>
    </head>
    <body>

    <div class="hero-container">
        <img id="main-bg" class="bg-image" src="IMG_SRC_1">
        <div class="overlay"></div>
        
        <div class="thumbnails">
            <div class="thumb-wrapper active" onclick="changeSlide(0, this)">
                <img src="IMG_SRC_1">
            </div>
            <div class="thumb-wrapper" onclick="changeSlide(1, this)">
                <img src="IMG_SRC_2">
            </div>
            <div class="thumb-wrapper" onclick="changeSlide(2, this)">
                <img src="IMG_SRC_3">
            </div>
            <div class="thumb-wrapper" onclick="changeSlide(3, this)">
                <img src="IMG_SRC_4">
            </div>
        </div>

        <div class="text-content">
            <h1 id="main-title">万里长城</h1>
            <p id="main-desc">世界文化遗产，中华民族的精神象征与智慧结晶，跨越千年的防御工程奇迹。</p>
        </div>
    </div>

    <script>
        const slides = [
            { img: 'IMG_SRC_1', title: '万里长城', desc: '世界文化遗产，中华民族的精神象征与智慧结晶，跨越千年的防御工程奇迹。' },
            { img: 'IMG_SRC_2', title: '北京故宫', desc: '世界文化遗产，明清两代皇家宫殿，中国古代宫廷建筑之精华，无与伦比的历史杰作。' },
            { img: 'IMG_SRC_3', title: '杭州西湖', desc: '世界文化景观遗产，秀丽的自然风光与深厚的文化底蕴完美融合，江南水乡的代表。' },
            { img: 'IMG_SRC_4', title: '秦始皇陵兵马俑', desc: '世界文化遗产，被誉为“世界第八大奇迹”，展现了秦代高超的雕塑艺术与大一统气象。' }
        ];

        function changeSlide(index, element) {
            const bg = document.getElementById('main-bg');
            const title = document.getElementById('main-title');
            const desc = document.getElementById('main-desc');
            
            document.querySelectorAll('.thumb-wrapper').forEach(el => el.classList.remove('active'));
            element.classList.add('active');

            bg.style.opacity = 0;
            setTimeout(() => {
                bg.src = slides[index].img;
                title.innerText = slides[index].title;
                desc.innerText = slides[index].desc;
                bg.style.opacity = 1;
            }, 400); 
        }
    </script>
    </body>
    </html>
    """
    # 将本地图片的 base64 注入进 HTML
    final_html = html_template.replace("IMG_SRC_1", img1).replace("IMG_SRC_2", img2).replace("IMG_SRC_3", img3).replace("IMG_SRC_4", img4)
    components.html(final_html, height=580)


# ================= 页面二：地图与数据大屏 =================
elif page == "遗产分布图":
    st.markdown('<h1 class="main-title">中国世界遗产分布大屏</h1>', unsafe_allow_html=True)
    st.markdown('<h3 class="sub-title">宏观数据统计与省级名录动态查询</h3>', unsafe_allow_html=True)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown('<div class="metric-card"><h2>60 项</h2><p>中国世界遗产总数</p></div>', unsafe_allow_html=True)
    with col2:
        st.markdown('<div class="metric-card"><h2>41 项</h2><p>世界文化遗产</p></div>', unsafe_allow_html=True)
    with col3:
        st.markdown('<div class="metric-card"><h2>15 项</h2><p>世界自然遗产</p></div>', unsafe_allow_html=True)
    with col4:
        st.markdown('<div class="metric-card"><h2>4 项</h2><p>文化与自然双重遗产</p></div>', unsafe_allow_html=True)

    st.write("---")

    @st.cache_data
    def load_china_map():
        url = "https://geo.datav.aliyun.com/areas_v3/bound/100000_full.json"
        return requests.get(url).json()

    map_obj = Map("china", load_china_map())
    map_col, list_col = st.columns([1.2, 1])

    all_provinces = ["北京市", "天津市", "河北省", "山西省", "内蒙古自治区", "辽宁省", "吉林省", "黑龙江省", "上海市", "江苏省", "浙江省", "安徽省", "福建省", "江西省", "山东省", "河南省", "湖北省", "湖南省", "广东省", "广西壮族自治区", "海南省", "重庆市", "四川省", "贵州省", "云南省", "西藏自治区", "陕西省", "甘肃省", "青海省", "宁夏回族自治区", "新疆维吾尔自治区", "台湾省", "香港特别行政区", "澳门特别行政区"]

    with map_col:
        st.markdown('<h3 style="color:#5C1D16;">交互地图 (点击省份下钻)</h3>', unsafe_allow_html=True)
        
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
            "visualMap": {
                "min": 0, "max": 8,
                "text": ["遗产多", "无遗产"],
                "realtime": False,
                "calculable": True,
                "inRange": {"color": ["#FDF8F5", "#E6BA89", "#C17942", "#8B3E04"]},
                "textStyle": {"color": "#666666"}
            },
            "series": [{
                "name": "遗产数量",
                "type": "map",
                "mapType": "china",
                "roam": True,
                "zoom": 1.3,
                "label": {"show": False, "color": "#111"},
                "itemStyle": {"areaColor": "#FDF8F5", "borderColor": "#CCCCCC"},
                "emphasis": {"label": {"show": True, "color": "#FFF", "fontWeight": "bold"}, "itemStyle": {"areaColor": "#5C2600"}},
                "data": map_data
            }]
        }
        
        click_js = "function(params) { return params.name; }"
        clicked_data = st_echarts(map_options, map=map_obj, events={"click": click_js}, height="600px", key="china_map")

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
            st.info("👈 请在左侧地图点击高亮的省份，查看具体的遗产名录。你可以使用鼠标滚轮放大或缩小地图区域。")
        elif province_name not in heritage_data or (len(heritage_data[province_name]["文化"]) + len(heritage_data[province_name]["自然"]) + len(heritage_data[province_name]["双重"]) == 0):
            st.markdown(f'<h3 class="province-title">{province_name}</h3>', unsafe_allow_html=True)
            st.info("该省份暂未列入世界遗产名录，但华夏大地处处皆是历史，期待未来的发现与传承！")
        else:
            st.markdown(f'<h3 class="province-title">{province_name}</h3>', unsafe_allow_html=True)
            data = heritage_data[province_name]
            
            if data["文化"]:
                st.markdown('<div class="list-category">世界文化遗产</div>', unsafe_allow_html=True)
                for item in data["文化"]:
                    st.markdown(f'<div class="list-item">{item}</div>', unsafe_allow_html=True)
                    
            if data["自然"]:
                st.markdown('<div class="list-category">世界自然遗产</div>', unsafe_allow_html=True)
                for item in data["自然"]:
                    st.markdown(f'<div class="list-item">{item}</div>', unsafe_allow_html=True)
                    
            if data["双重"]:
                st.markdown('<div class="list-category">世界文化与自然双重遗产</div>', unsafe_allow_html=True)
                for item in data["双重"]:
                    st.markdown(f'<div class="list-item">{item}</div>', unsafe_allow_html=True)

# ================= 页面三：AI 大模型 =================
elif page == "AI：智游遗迹":
    st.markdown('<h1 class="main-title">AI：智游遗迹</h1>', unsafe_allow_html=True)
    st.markdown('<h3 class="sub-title">您的专属世界文化遗产智能导游。</h3>', unsafe_allow_html=True)
    st.info("🤖 AI 接口接入中... 敬请期待！")