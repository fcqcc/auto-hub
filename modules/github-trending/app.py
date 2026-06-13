"""
GitHub + Gitee 趋势排行榜 - Flask App
"""
import json
from flask import Flask, render_template, jsonify
from scraper import get_all_trending

app = Flask(__name__)


@app.route('/')
def index():
    """主页面"""
    return render_template('index.html')


@app.route('/trending/api/trending/<since>')
def api_trending(since):
    """API 接口，返回 JSON 数据
    since: daily / weekly / monthly
    """
    if since not in ('daily', 'weekly', 'monthly'):
        since = 'daily'
    data = get_all_trending(since)
    return jsonify(data)


@app.route('/trending/api/trending')
def api_trending_default():
    """默认 daily"""
    return api_trending('daily')


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5051, debug=True)
