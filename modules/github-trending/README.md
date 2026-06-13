# 开源趋势排行榜

GitHub + Gitee 双源的开源项目趋势排行榜。Flask 一键启动，暗色暖橙 UI。

## 功能

- **双模式**：上升榜（按新增 Star）/ 总榜（按 Star 总数）
- **时间切换**：今日 / 本周 / 本月
- **分类筛选**：12 类（AI/ML、开发工具、Web 框架等）
- **双源数据**：GitHub Trending（爬虫）+ Gitee Search API
- **缓存系统**：5 分钟 TTL + 过期兜底
- **描述翻译**：DashScope API（可选，无 Key 跳过）

## 快速启动

```bash
# 安装依赖
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 启动
python app.py

# 访问
# http://localhost:5051
# API: http://localhost:5051/trending/api/trending/daily
#      http://localhost:5051/trending/api/trending/weekly
#      http://localhost:5051/trending/api/trending/monthly
```

## 文件结构

```
github-trending/
├── scraper.py           # 数据抓取 + 缓存 + 分类 + 翻译
├── app.py               # Flask 后端
├── templates/
│   └── index.html       # 前端页面
├── docs/
│   └── 开源趋势排行榜-一键指令.md  # AI 一键生成指南
├── requirements.txt     # Python 依赖
└── README.md            # 本文件
```

## 配置

可选：`DASHSCOPE_API_KEY` 环境变量，用于自动翻译英文描述。

```bash
# Windows (cmd)
set DASHSCOPE_API_KEY=sk-xxx

# Linux/macOS
export DASHSCOPE_API_KEY=sk-xxx
```

无 Key 不影响核心功能。
