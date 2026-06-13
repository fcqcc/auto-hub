"""
GitHub + Gitee Trending 爬虫
- 支持重试和缓存兜底
- 解析 "821 stars today" 等格式
"""

import requests
from bs4 import BeautifulSoup
import json
import os
import re
import time
from datetime import datetime, timedelta
from pathlib import Path

CACHE_DIR = Path(__file__).parent / 'cache'
CACHE_DIR.mkdir(exist_ok=True)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                  'AppleWebKit/537.36 (KHTML, like Gecko) '
                  'Chrome/120.0.0.0 Safari/537.36'
}

CACHE_TTL = 300  # 5分钟
MAX_RETRIES = 2


def _extract_number(text):
    """从文本中提取数字，支持多种格式"""
    if not text:
        return 0
    text = text.strip().replace(',', '')
    # "821 stars today" → 821
    m = re.search(r'(\d+(?:\.\d+)?)', text)
    if not m:
        return 0
    val = m.group(1)
    # 处理 "1.2k" / "12.3k"
    if 'k' in text.lower():
        return int(float(val) * 1000)
    return int(float(val))


def _load_cache(key):
    """读取缓存，过期或不存在返回 None"""
    path = CACHE_DIR / f'{key}.json'
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding='utf-8'))
            if time.time() - data['ts'] < CACHE_TTL:
                return data['items']
        except:
            pass
    return None


def _load_stale_cache(key):
    """读取过期缓存（兜底用，网络失败时返回旧数据而不是空）"""
    path = CACHE_DIR / f'{key}.json'
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding='utf-8'))
            return data['items']
        except:
            pass
    return None


def _save_cache(key, items):
    """写入缓存"""
    path = CACHE_DIR / f'{key}.json'
    path.write_text(
        json.dumps({'ts': time.time(), 'items': items}, ensure_ascii=False),
        encoding='utf-8'
    )


# ─── GitHub Trending ─────────────────────────────────────────────

def scrape_github_trending(since='daily'):
    """抓取 GitHub Trending
    since: daily / weekly / monthly
    """
    cache_key = f'gh_{since}'
    cached = _load_cache(cache_key)
    if cached:
        return cached

    url = f'https://github.com/trending?since={since}'

    for attempt in range(MAX_RETRIES + 1):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=(10, 20))
            resp.raise_for_status()
            break
        except Exception as e:
            print(f'[GitHub] 第{attempt+1}次失败: {e}')
            if attempt < MAX_RETRIES:
                time.sleep(2)
            else:
                # 返回过期缓存，有比没有好
                stale = _load_stale_cache(cache_key)
                if stale:
                    print(f'[GitHub] 使用过期缓存 ({cache_key})')
                    return stale
                return _fallback_empty('GitHub')
    else:
        stale = _load_stale_cache(cache_key)
        if stale:
            return stale
        return _fallback_empty('GitHub')

    soup = BeautifulSoup(resp.text, 'html.parser')
    articles = soup.select('article.Box-row')
    repos = []

    for article in articles:
        try:
            h2 = article.select_one('h2 a')
            if not h2:
                continue
            full_name = h2.get('href', '').strip('/')
            repo_url = f'https://github.com/{full_name}'

            desc_el = article.select_one('p')
            description = desc_el.text.strip() if desc_el else ''

            lang_el = article.select_one('[itemprop="programmingLanguage"]')
            language = lang_el.text.strip() if lang_el else ''

            # Star 总数
            star_el = article.select_one('.octicon-star')
            # 找到 star 旁边的数字
            stars = 0
            if star_el:
                parent = star_el.find_parent()
                if parent:
                    stars_text = parent.get_text(strip=True)
                    stars = _extract_number(stars_text)

            # Fork 数
            fork_el = article.select_one('.octicon-repo-forked')
            forks = 0
            if fork_el:
                parent = fork_el.find_parent()
                if parent:
                    forks = _extract_number(parent.get_text(strip=True))

            # 增长数（"X stars today"）
            growth = 0
            growth_container = article.select_one('.d-inline-block.float-sm-right')
            if growth_container:
                growth = _extract_number(growth_container.get_text(strip=True))
            if not growth:
                # 备选: 找包含 "stars today" 的文本
                article_text = article.get_text()
                m = re.search(r'(\d[\d,]*)\s*stars?\s*today', article_text, re.IGNORECASE)
                if m:
                    growth = _extract_number(m.group(1))

            repos.append({
                'name': full_name,
                'description': description[:200],
                'language': language,
                'stars': stars,
                'forks': forks,
                'growth': growth,
                'source': 'GitHub',
                'url': repo_url,
            })
        except Exception as e:
            print(f'[GitHub] 解析失败: {e}')
            continue

    if repos:
        _save_cache(cache_key, repos)
    else:
        stale = _load_stale_cache(cache_key)
        if stale:
            return stale

    return repos


# ─── Gitee Trending ──────────────────────────────────────────────

def scrape_gitee_trending():
    """抓取 Gitee Trending（用官方 API）"""
    cache_key = 'gitee'
    cached = _load_cache(cache_key)
    if cached:
        return cached

    # 尝试 Gitee 官方 API
    urls_to_try = [
        'https://gitee.com/api/v5/search/repos?q=a&sort=stars_count&order=desc&page=1&per_page=20',
        'https://gitee.com/api/v5/search/repos?q=b&sort=stars_count&order=desc&page=1&per_page=20',
    ]

    repos = []
    for url in urls_to_try:
        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
            if resp.status_code != 200:
                continue
            if '/api/' in url:
                # API 返回 JSON
                data = resp.json()
                items = data
                if isinstance(data, dict):
                    if 'data' in data:
                        items = data['data']
                    elif 'items' in data:
                        items = data['items']
                for item in (items if isinstance(items, list) else []):
                    if isinstance(item, dict):
                        # Gitee search API 字段
                        full_name = item.get('name', '') or item.get('path_with_namespace', '')
                        title = item.get('title', '')
                        # name 可能是 user/repo 或只有 repo 名
                        if not full_name and title and '/' not in title:
                            full_name = title
                        if not full_name:
                            continue
                        stars = item.get('stars', 0)
                        if isinstance(stars, str):
                            try:
                                stars = int(stars.replace(',', ''))
                            except:
                                stars = 0
                        repos.append({
                            'name': full_name,
                            'description': (item.get('description') or '')[:200],
                            'language': (item.get('language') or ''),
                            'stars': stars,
                            'forks': item.get('forks', 0),
                            'growth': stars,
                            'source': 'Gitee',
                            'url': item.get('html_url', '') or item.get('url', '') or f'https://gitee.com/{full_name}',
                        })
            else:
                # 网页解析（兜底，但大概率被反爬）
                continue
            if repos:
                break
        except Exception as e:
            print(f'[Gitee] {url[:40]} 失败: {e}')
            continue

    if repos:
        repos.sort(key=lambda r: r['stars'], reverse=True)
        _save_cache(cache_key, repos)
    else:
        stale = _load_stale_cache(cache_key)
        if stale:
            return stale

    return repos[:20]


def _fallback_empty(source):
    """爬取失败时返回空列表（前端自己处理）"""
    return []


# ─── GitHub API 备用 ──────────────────────────────────────────────

def scrape_github_api(since='daily'):
    """通过 GitHub Search API 获取趋势仓库（备用方案）
    当网页爬取失败时使用
    """
    cache_key = f'gh_api_{since}'
    cached = _load_cache(cache_key)
    if cached:
        return cached

    now = datetime.now()
    if since == 'daily':
        since_date = (now - timedelta(days=1)).strftime('%Y-%m-%d')
        # 今日新增项目（created>=昨天+stars>50，近似今日热门新项目）
        q = f'created:>={since_date} stars:>50'
    elif since == 'weekly':
        since_date = (now - timedelta(days=7)).strftime('%Y-%m-%d')
        q = f'created:>={since_date} stars:>200'
    else:  # monthly
        since_date = (now - timedelta(days=30)).strftime('%Y-%m-%d')
        q = f'created:>={since_date} stars:>500'

    url = 'https://api.github.com/search/repositories'
    params = {
        'q': q,
        'sort': 'stars',
        'order': 'desc',
        'per_page': 20,
    }

    try:
        resp = requests.get(url, headers={
            'Accept': 'application/vnd.github.v3+json',
            'User-Agent': 'Mozilla/5.0',
        }, timeout=15)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f'[GitHub API] 失败: {e}')
        stale = _load_stale_cache(cache_key)
        if stale:
            return stale
        return []

    repos = []
    for item in data.get('items', []):
        repos.append({
            'name': item.get('full_name', ''),
            'description': (item.get('description') or '')[:200],
            'language': item.get('language') or '',
            'stars': item.get('stargazers_count', 0),
            'forks': item.get('forks_count', 0),
            'growth': item.get('stargazers_count', 0),  # API版用 stars 当 growth
            'source': 'GitHub',
            'url': item.get('html_url', ''),
        })

    if repos:
        # 按 stars 降序，毕竟没有真正的 growth 数据
        repos.sort(key=lambda r: r['stars'], reverse=True)
        _save_cache(cache_key, repos)
    return repos


# ─── 项目分类 ──────────────────────────────────────────────────────

CATEGORY_RULES = [
    # (category_id, keywords_in_name_and_description, languages)
    ('ai-ml', [
        'ai', 'artificial intelligence', 'machine learning', 'deep learning',
        'llm', 'gpt', 'chatgpt', 'neural', 'model', 'transformer',
        'diffusion', 'stable diffusion', 'nlp', 'language model',
        'rag', 'agent', 'autonomous', 'tensorflow', 'pytorch',
        'openai', 'claude', 'gemini', 'mistral', 'langchain',
        'fine-tun', 'training', 'inference', 'embedding', 'vector',
        'llama', 'qwen', 'deepseek', 'chatbot', 'copilot',
    ]),
    ('dev-tools', [
        'cli', 'command line', 'terminal', 'debugger', 'linter',
        'formatter', 'code review', 'ide', 'editor', 'plugin',
        'extension', 'package manager', 'build tool', 'bundler',
        'compiler', 'transpiler', 'static analysis', 'testing',
        'git', 'github', 'changelog', 'dependency', 'version',
        'sdk', 'api client', 'rest', 'graphql', 'openapi',
        'swagger', 'documentation', 'tutorial', 'cheat sheet',
        'awesome', 'list', 'roadmap', 'developer', 'devtool',
    ]),
    ('web', [
        'react', 'vue', 'angular', 'svelte', 'next.js', 'nuxt',
        'remix', 'solid', 'astro', 'htmx', 'alpine', 'tailwind',
        'bootstrap', 'css', 'html', 'web', 'frontend', 'front-end',
        'backend', 'back-end', 'full-stack', 'full stack', 'webapp',
        'web app', 'website', 'browser', 'dom', 'spa', 'ssr',
        'ssg', 'server component', 'web component', 'ui framework',
    ]),
    ('infra', [
        'docker', 'kubernetes', 'k8s', 'container', 'orchestrat',
        'cloud', 'aws', 'gcp', 'azure', 'serverless', 'microservice',
        'devops', 'ci/cd', 'deploy', 'infrastructure', 'terraform',
        'ansible', 'monitoring', 'observability', 'prometheus',
        'grafana', 'logging', 'metric', 'alert', 'load balancer',
        'proxy', 'gateway', 'reverse proxy', 'nginx', 'caddy',
        'vpn', 'dns', 'network', 'cluster',
    ]),
    ('database', [
        'database', 'sql', 'nosql', 'redis', 'postgres', 'postgresql',
        'mysql', 'mongodb', 'sqlite', 'elasticsearch', 'clickhouse',
        'duckdb', 'cassandra', 'dynamodb', 'bigquery', 'snowflake',
        'data warehouse', 'data lake', 'etl', 'data pipeline',
        'delta lake', 'iceberg', 'lakehouse', 'index', 'query',
        'orm', 'odm', 'prisma', 'drizzle', 'sequelize',
    ]),
    ('data-ai', [
        'data science', 'data analysis', 'data visualization',
        'analytics', 'bi', 'business intelligence', 'dashboard',
        'chart', 'plot', 'graph', 'jupyter', 'notebook', 'pandas',
        'numpy', 'scipy', 'matplotlib', 'seaborn', 'plotly',
        'tableau', 'superset', 'metabase', 'statistics',
    ]),
    ('security', [
        'security', 'hack', 'penetration', 'vulnerability',
        'exploit', 'malware', 'ransomware', 'cryptography',
        'encrypt', 'decrypt', 'authentication', 'authorization',
        'oauth', 'jwt', 'zero trust', 'firewall', 'intrusion',
        'audit', 'compliance', 'gdpr', 'privacy', 'secret',
        'key management', 'certificate', 'ssl', 'tls',
    ]),
    ('mobile', [
        'android', 'ios', 'flutter', 'react native', 'kotlin',
        'swift', 'mobile', 'app', 'pwa', 'progressive web',
        'wearable', 'tablet', 'ipad', 'iphone',
    ]),
    ('blockchain', [
        'blockchain', 'ethereum', 'solana', 'web3', 'crypto',
        'nft', 'defi', 'smart contract', 'solidity', 'bitcoin',
        'wallet', 'dapp', 'dao', 'token', 'decentralized',
    ]),
    ('game', [
        'game', 'gaming', 'unity', 'unreal', 'godot', 'sprite',
        'pixel art', 'rpg', 'fps', '3d', 'opengl', 'vulkan',
        'directx', 'webgl', 'three.js', 'babylon', 'raylib',
        'emulator', 'rom', 'retro', 'console',
    ]),
    ('media', [
        'image', 'video', 'audio', 'music', 'sound', 'speech',
        'photo', 'editor', 'processing', 'filter', 'effect',
        'animation', 'svg', 'canvas', 'render', '3d',
        'ffmpeg', 'stream', 'codec', 'compression',
    ]),
    ('automation', [
        'automation', 'scraper', 'crawler', 'spider', 'bot',
        'workflow', 'pipeline', 'cron', 'scheduler', 'rpa',
        'selenium', 'playwright', 'puppeteer', 'cheerio',
    ]),
]

CATEGORY_META = {
    'ai-ml':       {'label': 'AI/ML',       'color': '#a855f7', 'emoji': '🤖'},
    'dev-tools':   {'label': '开发工具',     'color': '#3b82f6', 'emoji': '🔧'},
    'web':         {'label': 'Web 框架',     'color': '#06b6d4', 'emoji': '🌐'},
    'infra':       {'label': '基础设施',     'color': '#14b8a6', 'emoji': '☁️'},
    'database':    {'label': '数据库',       'color': '#eab308', 'emoji': '🗄️'},
    'data-ai':     {'label': '数据科学',     'color': '#f97316', 'emoji': '📊'},
    'security':    {'label': '安全',         'color': '#ef4444', 'emoji': '🔒'},
    'mobile':      {'label': '移动端',       'color': '#8b5cf6', 'emoji': '📱'},
    'blockchain':  {'label': 'Web3',         'color': '#f59e0b', 'emoji': '⛓️'},
    'game':        {'label': '游戏',         'color': '#22c55e', 'emoji': '🎮'},
    'media':       {'label': '媒体/设计',    'color': '#ec4899', 'emoji': '🎨'},
    'automation':  {'label': '自动化',       'color': '#6366f1', 'emoji': '⚡'},
    'other':       {'label': '其他',         'color': '#6b7280', 'emoji': '📦'},
}


def classify_repo(repo):
    """根据仓库 name + description 分类"""
    text = f"{repo['name']} {repo['description']}".lower()
    lang = (repo.get('language') or '').lower()

    for cat_id, keywords in CATEGORY_RULES:
        for kw in keywords:
            if kw in text:
                return cat_id
    return 'other'


def apply_classification(repos):
    """给一组 repo 打上分类标签"""
    for r in repos:
        cat_id = classify_repo(r)
        meta = CATEGORY_META.get(cat_id, CATEGORY_META['other'])
        r['category'] = cat_id
        r['category_label'] = meta['label']
        r['category_color'] = meta['color']
        r['category_emoji'] = meta['emoji']
    return repos


def collect_categories(repos):
    """从一组 repo 中提取出现的分类（按数量排序）"""
    from collections import Counter
    counts = Counter(r.get('category', 'other') for r in repos)
    return [
        {'id': cid, 'count': cnt, **CATEGORY_META.get(cid, CATEGORY_META['other'])}
        for cid, cnt in counts.most_common()
    ]


# ─── 描述翻译（DashScope / 通义千问） ─────────────────────────────

TRANS_CACHE = CACHE_DIR / 'translations.json'

def _load_trans_cache():
    if TRANS_CACHE.exists():
        try:
            return json.loads(TRANS_CACHE.read_text(encoding='utf-8'))
        except:
            return {}
    return {}

def _save_trans_cache(cache):
    TRANS_CACHE.write_text(json.dumps(cache, ensure_ascii=False), encoding='utf-8')

def _is_english(text):
    """判断一段文本是否以英文为主（需要翻译）"""
    if not text:
        return False
    # 如果超过 30% 的字符是 ASCII 字母，认为需要翻译
    letters = sum(1 for c in text if c.isalpha())
    ascii_letters = sum(1 for c in text if c.isascii() and c.isalpha())
    return letters > 0 and (ascii_letters / letters) > 0.3


def _get_dashscope_key():
    """获取 DashScope API Key，优先环境变量，其次 .env 文件"""
    key = os.environ.get('DASHSCOPE_API_KEY')
    if key:
        return key
    # 尝试从项目 .env 文件读取
    env_path = Path(__file__).parent / '.env'
    if env_path.exists():
        for line in env_path.read_text(encoding='utf-8').splitlines():
            line = line.strip()
            if line.startswith('DASHSCOPE_API_KEY='):
                return line.split('=', 1)[1].strip().strip("'\"")
    # 尝试从 /opt/auto-daily/.env 读取
    auto_env = Path('/opt/auto-daily/.env')
    if auto_env.exists():
        for line in auto_env.read_text(encoding='utf-8').splitlines():
            line = line.strip()
            if line.startswith('DASHSCOPE_API_KEY='):
                return line.split('=', 1)[1].strip().strip("'\"")
    return None


def translate_descriptions(repos):
    """批量翻译英文描述为中文，使用 DashScope 通义千问"""
    api_key = _get_dashscope_key()
    if not api_key:
        return repos  # 无 API key，跳过翻译

    # 收集需要翻译的描述
    cache = _load_trans_cache()
    need_translate = []  # [(repo_index, desc_key)]

    for i, r in enumerate(repos):
        desc = r.get('description', '')
        if not desc or not _is_english(desc):
            r['description_zh'] = ''
            continue
        # 用 (name, description) 做缓存 key
        cache_key = f"{r['name']}|{desc[:80]}"
        if cache_key in cache:
            r['description_zh'] = cache[cache_key]
        else:
            need_translate.append((i, cache_key, desc))

    if not need_translate:
        return repos

    # 批量翻译，分多次调用（每次不超过 20 条）
    batch_size = 20
    for start in range(0, len(need_translate), batch_size):
        batch = need_translate[start:start + batch_size]
        _batch_translate(batch, repos, cache, api_key)

    _save_trans_cache(cache)
    return repos


def _batch_translate(batch, repos, cache, api_key):
    """调用 DashScope 翻译一批描述"""
    # 构造翻译请求文本
    lines = []
    for idx, ck, desc in batch:
        lines.append(f'[{idx}] {desc}')
    input_text = '\n'.join(lines)

    prompt = (
        'You are a translator. Translate the following open-source project descriptions '
        'from English to Chinese. Keep technical terms (like "LLM", "API", "CLI", "GitHub") '
        'untranslated. Preserve the exact format: [number] text.\n\n'
        'Only output the translations, one per line, keeping the [number] prefix.\n\n'
        f'{input_text}'
    )

    try:
        resp = requests.post(
            'https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions',
            headers={
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json',
            },
            json={
                'model': 'qwen-turbo',
                'messages': [{'role': 'user', 'content': prompt}],
                'temperature': 0.1,
                'max_tokens': 2000,
            },
            timeout=30,
        )
        if resp.status_code != 200:
            print(f'[翻译] API 失败: {resp.status_code} {resp.text[:200]}')
            return

        result = resp.json()
        translated_text = result['choices'][0]['message']['content'].strip()

        # 解析返回的翻译结果
        for line in translated_text.split('\n'):
            line = line.strip()
            if not line or ']' not in line:
                continue
            try:
                num_str = line[:line.index(']')]
                num = int(num_str.strip('['))
                trans = line[line.index(']') + 1:].strip()
                # 找到对应的 batch 条目
                for idx, ck, desc in batch:
                    if idx == num:
                        repos[idx]['description_zh'] = trans
                        cache[ck] = trans
                        break
            except (ValueError, IndexError):
                continue

        print(f'[翻译] ✓ 完成 {len(batch)} 条')

    except Exception as e:
        print(f'[翻译] 请求异常: {e}')


# ─── 汇总 ────────────────────────────────────────────────────────

def get_all_trending(since='daily'):
    """获取完整趋势数据"""
    # 先试网页爬取（有 growth 数据）
    gh = scrape_github_trending(since)

    # 网页爬取失败时，用 API 备用
    if not gh:
        api_repos = scrape_github_api(since)
        if api_repos:
            gh = api_repos

    gt = scrape_gitee_trending()

    # 应用分类
    gh = apply_classification(gh)
    gt = apply_classification(gt)

    # 翻译英文描述为中文
    all_repos = gh + gt
    translate_descriptions(all_repos)

    combined = sorted(all_repos, key=lambda r: r.get('growth', 0) or r.get('stars', 0), reverse=True)

    return {
        'github': gh[:20],
        'gitee': gt[:20],
        'trending': combined,
        'categories': collect_categories(combined),
        'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    }
