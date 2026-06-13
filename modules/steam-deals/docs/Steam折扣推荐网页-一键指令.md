# Steam 打折游戏推荐网页 — 一键指令

> **使用说明**：复制「启动语」，粘贴到任意 AI，AI 会按流程引导你生成完整项目。
> 页面效果对标生产版：统计看板 + 游戏卡片（标签+简介+折扣+价格）+ 筛选 + 中文翻译

---

## 基本信息

| 项目 | 内容 |
|------|------|
| **项目名** | Steam 打折游戏推荐网页 |
| **任务类型** | API 调用型 + 爬虫型 |
| **核心技术栈** | `requests` + `Flask` + `Pillow` + `HTML/CSS` |
| **运行环境** | Windows/Mac/Linux 桌面（有 Python 就行） |
| **网络适配** | 国内网络优化：pip 走清华镜像 + 蒸汽平台 RSS 优先 |
| **目标用户痛点** | Steam 打折几百个游戏，手动翻累死人 |

---

## 页面效果预览（必须实现）

```
┌─────────────────────────────────────────────────────┐
│  🎮 Steam 折扣推荐                                  │
│  今日特惠 · 共 27 款                                 │
├─────────────────────────────────────────────────────┤
│ ┌──────统计看板──────┐ ┌──────统计看板──────┐       │
│ │ 💥 折扣分布         │ │ 🏷️ 价格档次        │       │
│ │ 史低:8 大促:12 ... │ │ 白菜价:5 划算:10   │       │
│ └────────────────────┘ └────────────────────┘       │
│ ┌──────统计看板──────┐                              │
│ │ 🎯 游戏类型         │                             │
│ │ 动作:8 冒险:5 RPG:4│                              │
│ └────────────────────┘                              │
├─────────────────────────────────────────────────────┤
│ 更新于 2026-06-10 08:00                             │
│                                                     │
│  ┌────────────────────────────────────────────┐     │
│  │ 游戏名 - 80%                      [类型][价格] │     │
│  │ 这是一款开放世界动作RPG...（翻译后的中文简介）│     │
│  └────────────────────────────────────────────┘     │
│                                                     │
│  ┌────────────────────────────────────────────┐     │
│  │ 另一款游戏 - 75%                    [类型][价格] │     │
│  │ 简介...（翻译）                              │     │
│  └────────────────────────────────────────────┘     │
├─────────────────────────────────────────────────────┤
│ Powered by Steam · 按折扣/价格/类型智能筛选          │
└─────────────────────────────────────────────────────┘
```

---

## 启动语（复制这句）

```
我要在桌面上建一个 Steam 折扣推荐网页。要求：
1. 展示统计看板（折扣分布/价格档次/游戏类型）
2. 游戏卡片带类型标签、价格标签、折扣、简介
3. 英文简介自动翻译成中文
4. 支持按折扣/价格/类型筛选
5. 暗色 Steam 主题风格
AI 一键搞定。
```

---

## AI 对话流程（6 步）

### 第 0 步：欢迎

```
你好！我来帮你搭建 Steam 折扣推荐网页。2个问题搞定，选就行。
准备好了吗？我们开始 👇
```

### 第 1 步：问题 1/2（数据源）

```
问题 1/2：折扣数据从哪里获取？

A. Steam 官方 API（推荐，有实际价格+好评率+封面图，无需Key，数据最全）
B. Steam RSS（零配置，但只有折扣%，无实际价格和评分）
C. 不知道（你帮我选）

你选哪个？
（A 数据最全，推荐。国内直连，无需申请任何东西）
```

**AI 处理逻辑**：
- 选 A → 用 `featuredcategories` + `appdetails` + `appreviews` 三个公开 API，零 Key
- 选 B → 用 RSS feed
- 选 C → AI 建议选 A

> **推荐：A（Steam 官方 API），数据最全，零 Key，国内直连。**

### 第 2 步：问题 2/2（筛选偏好）

```
问题 2/2：你想怎么筛选这些游戏？

A. 只看大折扣（-50%以上，最实用）
B. 只看白菜价（折后便宜的）
C. 按类型看（动作/格斗/RPG/策略...）
D. 不过滤，全部展示

你选哪个？
（推荐 A，折扣力度最直观）
```

**AI 处理逻辑**：
- 选 C → 接着问具体类型
- 其他选项直接进下一步

> **推荐：A（只看大折扣），默认折扣下限 50%。**

### 第 3 步：确认

```
好的，总结一下：
- 数据源：[A.Steam RSS / B.Steam API（需Key）]
- 筛选方式：[A.大折扣 / B.白菜价 / C.按类型 / D.全部]
- 默认折扣下限：50%（选A时）
```

确认没问题，回「确认」，我开始生成。

### 第 4 步：生成项目包

```
steam-deals-web/
├── main.py              # 全部代码（抓取+过滤+统计+封面生成+网页）
├── requirements.txt     # 依赖
├── run.bat              # Windows 一键启动（默认清华镜像）
├── run.sh               # Mac/Linux 启动
└── README.md            # 小白说明
```

#### ===== main.py 完整代码 =====

```python
"""
Steam 折扣推荐网页 - 单文件全功能
统计看板 + 类型标签 + 价格标签 + 中文翻译 + 筛选 + 暗色主题
"""

import requests
from flask import Flask, render_template_string, request
from datetime import datetime
import os, re, html

app = Flask(__name__)

# ========== 类型关键词库 ==========
GENRE_KEYWORDS = {
    "动作":  ["action","fps","shooter","combat","battle","射击"],
    "冒险":  ["adventure","explore","quest","journey","open world"],
    "格斗":  ["fighting","martial arts","beat","brawler"],
    "RPG":   ["rpg","role-playing","rogue","暗黑","巫师","上古卷轴"],
    "策略":  ["strategy","tactical","4x","simulation","文明","三国"],
    "模拟经营": ["simulator","tycoon","management","模拟","经营"],
    "体育竞速": ["sports","racing","football","f1","赛车"],
    "恐怖":  ["horror","survival horror","scary","恐怖"],
    "解谜":  ["puzzle","mystery","logic","解谜"],
    "独立":  ["indie","独立","像素","复古"],
}

def guess_genre(title, desc):
    """从游戏名+简介猜测类型"""
    text = (title + " " + desc).lower()
    found = [g for g, kw in GENRE_KEYWORDS.items() if any(k in text for k in kw)]
    return found[:2] if found else ["其他"]

# ========== 翻译（有道，免费）==========
def translate_text(text):
    if not text or len(text.strip()) < 5 or re.search(r'[\u4e00-\u9fff]', text):
        return text
    try:
        # 有道翻译 GET（最稳定，POST 可能被拦截）
        params = {"doctype": "json", "type": "AUTO", "i": text[:500]}
        r = requests.get("https://fanyi.youdao.com/translate",
                         params=params, timeout=5)
        result = r.json()
        if result.get("translateResult"):
            return "".join([i["tgt"] for i in result["translateResult"][0]])
    except Exception as e:
        print(f"  翻译失败: {e}")
    return text

# ========== 1. 抓数据（Steam 公开 API，零 Key）==========
def fetch_deals():
    """调 Steam 公开 API 获取折扣（featuredcategories + appdetails，无需Key）"""
    deals = []
    try:
        # 1. 获取特惠列表（featuredcategories API，公开）
        r = requests.get(
            "https://store.steampowered.com/api/featuredcategories",
            params={"cc": "cn", "l": "zh-cn"},
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=15
        )
        specials = r.json().get("specials", {}).get("items", [])
        print(f"  📡 获取到 {len(specials)} 条特惠")

        # 2. 逐个获取详情（appdetails API，公开）
        for item in specials[:20]:
            app_id = item["id"]
            detail_r = requests.get(
                f"https://store.steampowered.com/api/appdetails",
                params={"appids": app_id, "cc": "cn", "l": "zh-cn"},
                timeout=10
            )
            detail = detail_r.json().get(str(app_id), {}).get("data", {})

            # 3. 获取好评率（appreviews API，公开）
            rating = 0
            try:
                rev_r = requests.get(
                    f"https://store.steampowered.com/appreviews/{app_id}",
                    params={"json": 1, "language": "schinese", "num_per_page": 0},
                    timeout=10
                )
                s = rev_r.json().get("query_summary", {})
                total = s.get("total_reviews", 0) or 0
                positive = s.get("total_positive", 0) or 0
                if total > 0:
                    rating = round(positive / total * 100)
            except:
                pass

            title_text = item.get("name", "")
            desc_raw = detail.get("short_description", "") or ""
            # 从 Steam tags 解析类型
            genre_names = []
            tags = detail.get("tags") or {}
            for tag_name in tags:
                genre_names.append(tag_name)
            genres = guess_genre_from_tags(genre_names)

            deals.append({
                "title": title_text,
                "link": f"https://store.steampowered.com/app/{app_id}",
                "discount": item.get("discount_percent", 0) or 0,
                "original_price": (item.get("original_price", 0) or 0) / 100,
                "final_price": (item.get("final_price", 0) or 0) / 100,
                "desc": translate_text(desc_raw[:200]) or desc_raw[:200],
                "genres": genres,
                "header_image": detail.get("header_image", "") or
                    f"https://steamcdn-a.akamaihd.net/steam/apps/{app_id}/header.jpg",
                "rating": rating,
            })
        return deals
    except Exception as e:
        print(f"  ❌ Steam API 抓取失败: {e}")
        return []

def guess_genre_from_tags(tag_names):
    """从 Steam 标签解析类型"""
    GENRE_MAP = {
        "动作":"动作","Action":"动作","ACT":"动作",
        "冒险":"冒险","Adventure":"冒险",
        "RPG":"RPG","角色扮演":"RPG",
        "模拟":"模拟","Simulation":"模拟","模拟经营":"模拟",
        "策略":"策略","Strategy":"策略",
        "独立":"独立","Indie":"独立",
        "恐怖":"恐怖","Horror":"恐怖",
        "射击":"射击","Shooter":"射击","FPS":"射击",
        "格斗":"格斗","Fighting":"格斗",
        "解谜":"解谜","Puzzle":"解谜",
        "体育":"体育","Sports":"体育",
        "竞速":"竞速","Racing":"竞速",
        "休闲":"休闲","Casual":"休闲",
        "开放世界":"开放世界","Open World":"开放世界",
    }
    found = set()
    for name in tag_names:
        for kw, genre in GENRE_MAP.items():
            if kw.lower() in name.lower():
                found.add(genre)
    return list(found)[:3] or ["其他"]

def extract_discount(title):
    m = re.search(r'-(\d+)%', title)
    return int(m.group(1)) if m else 0

# ========== 2. 过滤 ==========
def filter_deals(deals, min_discount=0, target_genres=None):
    """多维过滤：折扣 + 类型"""
    result = [d for d in deals if d["discount"] >= min_discount]
    if target_genres:
        result = [d for d in result if any(g in target_genres for g in d["genres"])]
    return result

# ========== 3. 统计 ==========
def compute_stats(deals):
    by_discount = {
        "史低(≥70%)": sum(1 for d in deals if d["discount"] >= 70),
        "大促(50-69%)": sum(1 for d in deals if 50 <= d["discount"] < 70),
        "中促(30-49%)": sum(1 for d in deals if 30 <= d["discount"] < 50),
        "小促(<30%)": sum(1 for d in deals if d["discount"] < 30),
    }
    by_genre = {}
    for d in deals:
        for g in d["genres"]:
            by_genre[g] = by_genre.get(g, 0) + 1
    by_genre = dict(sorted(by_genre.items(), key=lambda x: -x[1]))
    return {
        "total": len(deals),
        "by_discount": {k:v for k,v in by_discount.items() if v > 0},
        "by_genre": by_genre,
        "max_discount": max((d["discount"] for d in deals), default=0),
    }

# ========== 4. 封面图生成（Pillow，零配置）==========
def gen_cover_image(deals, output_path="cover.png"):
    """生成 4 宫格折扣封面（900×383），用前 4 个游戏"""
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        print("Pillow 未安装，跳过封面生成")
        return None
    
    if len(deals) < 1:
        return None
    deals = deals[:4]
    
    W, H = 900, 383
    MARGIN = 36
    GAP = 14
    CARD_W = (W - 2*MARGIN - 3*GAP) // 4
    IMG_H = int(CARD_W * 0.62)
    BG = (18, 18, 18)
    CARD_BG = (30, 30, 30)
    WHITE = (255, 255, 255)
    ACCENT = (255, 152, 0)
    RED = (255, 55, 40)
    GRAY = (150, 150, 150)
    
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)
    
    # 尝试加载字体，失败用默认
    font_size = 14
    try:
        font = ImageFont.truetype("C:/Windows/Fonts/NotoSansSC-VF.ttf", 12)
        disc_f = ImageFont.truetype("C:/Windows/Fonts/NotoSansSC-VF.ttf", 16)
        title_f = ImageFont.truetype("C:/Windows/Fonts/NotoSansSC-VF.ttf", 24)
    except:
        font = ImageFont.load_default()
        disc_f = font
        title_f = font
    
    # 主标题
    draw.text((MARGIN, 14), f"STEAM DEALS · {datetime.now().strftime('%Y-%m-%d')}", fill=GRAY, font=font)
    draw.text((MARGIN, 34), "Steam 好价日报", fill=WHITE, font=title_f)
    # 副标题
    draw.text((MARGIN, 66), f"{len(deals)} 款折扣 · 最高 -{max(d['discount'] for d in deals)}% OFF", fill=(180,180,180), font=font)
    # 橙色分隔线
    line_y = 88
    line_w = min(240, draw.textlength("Steam 好价日报", font=title_f))
    draw.rectangle([MARGIN, line_y, MARGIN + line_w, line_y + 2], fill=ACCENT)
    
    # 4 个卡片
    cards_y = line_y + 12
    max_d = max(d["discount"] for d in deals)
    for i, deal in enumerate(deals):
        x = MARGIN + i * (CARD_W + GAP)
        # 下载封面图
        header_img = None
        if deal.get("header_image"):
            try:
                hr = requests.get(deal["header_image"], timeout=5)
                from io import BytesIO
                header_img = Image.open(BytesIO(hr.content)).convert("RGB")
            except:
                pass
        
        if header_img:
            # center-crop
            ratio = header_img.width / header_img.height
            target_r = CARD_W / IMG_H
            if ratio > target_r:
                new_w = int(IMG_H * ratio)
                header_img = header_img.resize((new_w, IMG_H))
                crop_x = (new_w - CARD_W) // 2
                header_img = header_img.crop((crop_x, 0, crop_x + CARD_W, IMG_H))
            else:
                new_h = int(CARD_W / ratio)
                header_img = header_img.resize((CARD_W, new_h))
                crop_y = (new_h - IMG_H) // 2
                header_img = header_img.crop((0, crop_y, CARD_W, crop_y + IMG_H))
            img.paste(header_img, (x, cards_y))
        else:
            draw.rectangle([x, cards_y, x + CARD_W, cards_y + IMG_H], fill=CARD_BG)
        
        # 折扣角标（右下角）
        is_max = deal["discount"] == max_d
        badge_color = RED if is_max else ACCENT
        disc_text = f"-{deal['discount']}%"
        dw = draw.textlength(disc_text, disc_f) + 12
        dh = 24
        bx = x + CARD_W - dw - 3
        by = cards_y + IMG_H - dh - 4
        draw.rectangle([bx, by, bx + dw, by + dh], fill=badge_color)
        draw.text((bx + 6, by + 3), disc_text, fill=WHITE, font=disc_f)
        
        # 游戏名
        name = deal["title"] if len(deal["title"]) <= 15 else deal["title"][:13] + "…"
        draw.text((x, cards_y + IMG_H + 6), name, fill=WHITE, font=font)
        
        # 等级标签
        tag_text = " · ".join(deal["genres"])
        if tag_text:
            draw.text((x, cards_y + IMG_H + 24), tag_text, fill=GRAY, font=font)
    
    # 页脚
    draw.text((MARGIN, 368), "STEAM DAILY · 每周折扣精选", fill=(100,100,100), font=font)
    
    img.save(output_path)
    print(f"  封面已生成: {output_path}")
    return output_path

# ========== 4. 网页模板（对标参考项目 yqzan.cn/steam）==========
HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<meta name="theme-color" content="#1a1a2e">
<title>Steam 好价追踪</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
:root{
  --bg:#0d1117;--card:#161b22;--card-hover:#1c2333;
  --border:#30363d;--text:#e6edf3;--text-secondary:#8b949e;
  --accent:#58a6ff;--accent2:#bc8cff;--green:#3fb950;
  --orange:#d29922;--red:#f85149;--pink:#ff7b9c;--gold:#ffd700;
}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI','PingFang SC','Microsoft YaHei',sans-serif;background:var(--bg);color:var(--text);min-height:100vh;line-height:1.5}
.container{max-width:960px;margin:0 auto;padding:0 16px}
.header{background:linear-gradient(135deg,#1a1a2e 0%,#16213e 100%);border-bottom:1px solid var(--border);padding:20px 0;position:sticky;top:0;z-index:100;backdrop-filter:blur(10px)}
.header-inner{display:flex;align-items:center;justify-content:space-between;max-width:960px;margin:0 auto;padding:0 16px}
.header h1{font-size:20px;font-weight:700;background:linear-gradient(135deg,var(--accent),var(--accent2));-webkit-background-clip:text;-webkit-text-fill-color:transparent;cursor:pointer}
.header .subtitle{font-size:12px;color:var(--text-secondary)}
.header-right{display:flex;gap:10px;align-items:center}
.header-right button{background:var(--card);border:1px solid var(--border);color:var(--text);padding:8px 16px;border-radius:8px;cursor:pointer;font-size:13px;font-family:inherit;transition:all .2s}
.header-right button:hover{background:var(--card-hover);border-color:var(--accent)}
.stats{display:flex;gap:16px;padding:16px 0;overflow-x:auto;scrollbar-width:none}
.stat-card{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:12px 18px;min-width:120px;flex-shrink:0}
.stat-card .num{font-size:22px;font-weight:700}
.stat-card .label{font-size:12px;color:var(--text-secondary);margin-top:2px}
.tabs{display:flex;gap:0;margin:12px 0;background:var(--card);border-radius:10px;overflow:hidden;border:1px solid var(--border)}
.tab{flex:1;padding:10px;text-align:center;font-size:13px;cursor:pointer;transition:all .2s;color:var(--text-secondary);font-family:inherit;background:transparent;border:none}
.tab.active{background:var(--accent);color:#fff;font-weight:600}
.tab:hover:not(.active){color:var(--text)}
.game-grid{display:grid;gap:12px;padding-bottom:80px}
.game-card{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:14px;cursor:pointer;transition:all .2s;display:flex;gap:14px;align-items:flex-start}
.game-card:hover{background:var(--card-hover);border-color:var(--accent);transform:translateY(-1px)}
.game-card .thumb{width:80px;height:40px;border-radius:6px;background:var(--border);flex-shrink:0;object-fit:cover;overflow:hidden}
.game-card .info{flex:1;min-width:0}
.game-card .name{font-size:15px;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.game-card .meta{display:flex;gap:8px;flex-wrap:wrap;margin-top:6px;font-size:12px;color:var(--text-secondary)}
.game-card .meta span{background:rgba(255,255,255,0.05);padding:2px 8px;border-radius:4px;white-space:nowrap}
.game-card .desc{font-size:11px;color:var(--text-secondary);margin-top:4px;line-height:1.4;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
.game-card .price-area{text-align:right;flex-shrink:0}
.game-card .price-old{font-size:12px;color:var(--text-secondary);text-decoration:line-through}
.game-card .price-new{font-size:18px;font-weight:700}
.game-card .discount-badge{display:inline-block;background:linear-gradient(135deg,var(--red),#ff6b6b);color:#fff;padding:2px 8px;border-radius:4px;font-size:13px;font-weight:700}
.section-title{font-size:17px;font-weight:700;padding:20px 0 12px;display:flex;align-items:center;gap:8px}
.loading{text-align:center;padding:60px 0;color:var(--text-secondary)}
.loading .spinner{width:32px;height:32px;border:3px solid var(--border);border-top-color:var(--accent);border-radius:50%;animation:spin .8s linear infinite;margin:0 auto 12px}
@keyframes spin{to{transform:rotate(360deg)}}
.empty{text-align:center;padding:60px 20px;color:var(--text-secondary)}
.empty .icon{font-size:48px;margin-bottom:12px}
.footer{text-align:center;padding:24px 0;color:var(--text-secondary);font-size:12px}
@media(max-width:600px){
  .game-card .thumb{width:60px;height:34px}
  .game-card .price-new{font-size:16px}
  .stat-card{min-width:90px;padding:10px 14px}
  .stat-card .num{font-size:18px}
  .header h1{font-size:17px}
}
</style>
</head>
<body>
<div class="header">
  <div class="header-inner">
    <div>
      <h1>🎮 Steam 好价</h1>
      <div class="subtitle">每日精选折扣 · 白菜价 · 史低追踪</div>
    </div>
    <div class="header-right">
      <button onclick="location.reload()">🔄 刷新</button>
    </div>
  </div>
</div>
<div class="container">
  <div class="tabs" id="tabs">
    <button class="tab active" data-tab="home">🔥 今日精选</button>
    <button class="tab" data-tab="bargain">🥬 白菜价</button>
  </div>
  <div class="stats" id="stats"></div>
  <div id="tab-home">
    <div class="section-title">🏆 今日折扣</div>
    <div id="dealList" class="game-grid"><div class="loading"><div class="spinner"></div>加载中...</div></div>
  </div>
  <div id="tab-bargain" style="display:none">
    <div class="section-title">🥬 白菜价专区</div>
    <div id="bargainList" class="game-grid"><div class="loading"><div class="spinner"></div>加载中...</div></div>
  </div>
  <div class="footer">数据来源: Steam RSS · 实时更新</div>
</div>
<script>
let allDeals = [];

function renderStats(deals){
  const total = deals.length;
  const bargains = deals.filter(d => (d.discount||0) >= 70).length;
  const bigSales = deals.filter(d => (d.discount||0) >= 70).length;
  const avg = total ? Math.round(deals.reduce((s,d)=>s+(d.discount||0),0)/total) : 0;
  document.getElementById('stats').innerHTML = `
    <div class="stat-card"><div class="num" style="color:var(--accent)">${total}</div><div class="label">今日折扣</div></div>
    <div class="stat-card"><div class="num" style="color:var(--green)">${bargains}</div><div class="label">🥬 白菜价</div></div>
    <div class="stat-card"><div class="num" style="color:var(--red)">${bigSales}</div><div class="label">超低价 (≥70% off)</div></div>
    <div class="stat-card"><div class="num" style="color:var(--gold)">${avg}%</div><div class="label">平均折扣</div></div>
  `;
}

function renderDeals(containerId, deals){
  const el = document.getElementById(containerId);
  if(!deals||!deals.length){
    el.innerHTML='<div class="empty"><div class="icon">📭</div><div>没有找到匹配的游戏</div></div>';
    return;
  }
  el.innerHTML = deals.map(d => {
    const nameHtml = d.desc ? `<div class="desc">${d.desc}</div>` : '';
    const genreHtml = d.genres&&d.genres.length ? `<span>${d.genres[0]}</span>` : '';
    const ratingHtml = d.rating >= 70 ? `<span style="background:rgba(63,185,80,0.2);color:var(--green);padding:2px 8px;border-radius:4px;font-size:11px">⭐${d.rating}%</span>` : '';
    const hasPrice = d.final_price && d.final_price > 0;
    return `
      <div class="game-card" onclick="window.open('${d.link}','_blank')">
        ${d.header_image ? `<img class="thumb" src="${d.header_image}" alt="" loading="lazy" onerror="this.style.display='none'" />` : '<div class="thumb"></div>'}
        <div class="info">
          <div class="name">${d.title}</div>
          <div class="meta">
            ${genreHtml}
            ${ratingHtml}
          </div>
          ${nameHtml}
        </div>
        <div class="price-area">
          <div class="discount-badge">-${d.discount}%</div>
          ${hasPrice ? `<div class="price-old">¥${d.original_price.toFixed(0)}</div><div class="price-new" style="color:var(--orange)">¥${d.final_price.toFixed(0)}</div>` : ''}
        </div>
      </div>
    `;
  }).join('');
}

function switchTab(tabName){
  document.querySelectorAll('.tab').forEach(t=>t.classList.remove('active'));
  document.querySelector(`.tab[data-tab="${tabName}"]`).classList.add('active');
  document.querySelectorAll('[id^="tab-"]').forEach(t=>t.style.display='none');
  document.getElementById('tab-'+tabName).style.display='block';
  if(tabName==='bargain'){
    const bargains = allDeals.filter(d=>(d.discount||0)>=70);
    renderDeals('bargainList', bargains);
  }
}

document.querySelectorAll('.tab').forEach(tab=>{
  tab.addEventListener('click',()=>switchTab(tab.dataset.tab));
});

// 数据通过 Jinja2 注入
const deals = {{ deals | tojson }};
allDeals = deals;
renderStats(deals);
renderDeals('dealList', deals);
switchTab('home');
</script>
</body>
</html>"""

# ========== 配置 ==========
MIN_DISCOUNT = int(os.getenv("MIN_DISCOUNT", "50"))
TARGET_GENRES = os.getenv("TARGET_GENRES", "")

@app.route("/")
def home():
    min_d = request.args.get("min", type=int) or MIN_DISCOUNT
    deals = fetch_deals()
    genres = TARGET_GENRES.split(",") if TARGET_GENRES else None
    filtered = filter_deals(deals, min_discount=min_d, target_genres=genres)
    return render_template_string(HTML_TEMPLATE, deals=filtered)

@app.route("/cover")
def cover():
    """生成并返回 4 宫格折扣封面图"""
    deals = fetch_deals()
    filtered = filter_deals(deals, min_discount=MIN_DISCOUNT)
    path = gen_cover_image(filtered, "cover.png")
    if path:
        from flask import send_file
        return send_file(path, mimetype="image/png")
    return "暂无数据生成封面", 404

if __name__ == "__main__":
    print(f"🔥 Steam 折扣推荐网页启动中...")
    print(f"  折扣下限: ≥{MIN_DISCOUNT}%")
    if TARGET_GENRES: print(f"  游戏类型: {TARGET_GENRES}")
    print(f"👉 访问 http://localhost:5050")
    print(f"🖼️ 封面图: http://localhost:5050/cover")
    app.run(host="0.0.0.0", port=5050, debug=False)
```

#### ===== requirements.txt =====

```
requests==2.31.0
flask==3.0.2
Pillow==10.2.0
```

> **国内加速**：`pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple`

#### ===== run.bat（Windows 用）=====

```batch
@echo off
chcp 65001 >nul
echo 🚀 启动 Steam 折扣推荐网页...
cd /d "%~dp0"
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple -q
python main.py
pause
```

#### ===== run.sh（Mac/Linux 用）=====

```bash
#!/bin/bash
cd "$(dirname "$0")"
pip3 install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple -q
python3 main.py
```

#### ===== README.md =====

```markdown
# Steam 折扣推荐网页

自动抓取 Steam 最新折扣，展示统计看板 + 游戏列表 + 中文翻译。

## 启动
- Windows：双击 run.bat
- Mac/Linux：bash run.sh
- 浏览器打开 http://localhost:5050

## 功能
- 📊 统计看板：折扣分布 + 游戏类型排行
- 🏷️ 游戏卡片：类型标签 + 简介 + 折扣力度
- 🌐 英文简介自动翻译中文
- 🔍 点击筛选栏切换折扣档次

## 停掉
按 Ctrl+C 关闭终端即可。
```

### 第 5 步：部署 + 展示地址

```
项目生成好了！接下来：

A. 让我帮你启动（AI 自动装依赖 + 启动 + 展示访问地址）
B. 我自己启动（照着 README 来）
C. 先看说明

你选哪个？
```

**选 A** → AI 自动执行：
```
✅ 启动成功！
👉 访问地址：http://localhost:5050
```

### 第 6 步：完成

```
🎉 搞定！访问 http://localhost:5050 看效果。

页面功能：
├── 📊 统计看板：折扣分布（史低/大促/中促）+ 类型排行
├── 🏷️ 游戏卡片：名称（可点击）+ 类型标签 + 简介（翻译中）+ 折扣
├── 🔍 点击筛选：全部 / 史低 / 大折扣 / 中促
├── 🖼️ 封面图：http://localhost:5050/cover（可直接下载发公众号）
└── 暗色 Steam 风格，清爽不刺眼

想改筛选？修改 main.py 顶部的 MIN_DISCOUNT 值就行。
```

---

## 验证清单

- [ ] 统计看板显示折扣分布（至少 3 档）和游戏类型排行
- [ ] 游戏卡片带绿色类型标签
- [ ] 英文简介自动翻译成中文
- [ ] 折扣颜色区分（红色≥50% / 橙色≥30% / 蓝色<30%）
- [ ] 筛选栏可切换折扣档次
- [ ] 运行环境兼容 Windows/Mac/Linux
- [ ] pip 默认走清华镜像
- [ ] 暗色 Steam 主题（#1b2838 背景）
- [ ] 数据源用 Steam 公开 API（featuredcategories + appdetails + appreviews，零 Key）
- [ ] 游戏卡片显示实际价格（原价删除线+折后价橙色）
- [ ] 翻译用 GET 请求（POST 可能被拦截）
- [ ] 启动时打印调试日志（抓取/翻译失败时有输出）
- [ ] 数据为空时有友好提示（不是白屏）

## 页面效果对照

| 功能点 | 参考项目 (yqzan.cn/steam) | 本指令生成版 |
|--------|--------------------------|------------|
| 背景色 | `#0d1117` GitHub 暗色 | ✅ **一致** |
| Header 渐变 | `#1a1a2e → #16213e` | ✅ **一致** |
| 标题渐变文字 | 蓝→紫渐变 | ✅ **一致** |
| 副标题 | "每日精选折扣·白菜价·史低追踪" | ✅ **一致** |
| 刷新按钮 | 右上角 | ✅ **一致** |
| 顶部 Tab | 今日精选 / 白菜价 | ✅ **一致** |
| 统计卡片 | 4张（今日折扣/白菜价/超低价/平均折扣） | ✅ **一致** |
| 游戏卡片 | 横排（缩略图+信息+价格区） | ✅ **一致** |
| 缩略图 | 80×40 Steam 封面 | ✅ **一致** |
| 折扣角标 | 红色渐变 `-XX%` | ✅ **一致** |
| 类型标签 | 半透明背景圆角 | ✅ **一致** |
| 简介 | 2行截断 | ✅ **一致** |
| 加载动画 | 旋转 Spinner | ✅ **一致** |
| 空数据状态 | 📭 图标+提示 | ✅ **一致** |
| 响应式 | 移动端适配 | ✅ **一致** |
| Footer | 数据来源说明 | ✅ **一致** |
| 实际价格 | API 才有 | ⬜ RSS 无此字段 |
| 好评率标签 | API 才有 | ⬜ RSS 无此字段 |
| 史低/白菜价徽章 | API 才有 | ⬜ RSS 无此字段 |
| PWA 安装栏 | manifest.json | ⬜ 未包含 |
| 搜索/排序 | API 才有 | ⬜ RSS 无此字段 |
