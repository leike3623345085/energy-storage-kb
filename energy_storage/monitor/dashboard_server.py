#!/usr/bin/env python3
# 任务执行实时监控面板 - 带本地依赖路径
import sys
import os

# 添加本地依赖路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'libs'))

from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, emit
import threading
import time
import json
from datetime import datetime

# 导入收集器
sys.path.insert(0, os.path.dirname(__file__))
from collector import TaskMonitorCollector

app = Flask(__name__)
app.config['SECRET_KEY'] = 'task-monitor-secret'
socketio = SocketIO(app, cors_allowed_origins="*")

# 初始化收集器
collector = TaskMonitorCollector()

# 后台数据推送线程
def background_push():
    """每5秒推送一次数据到所有客户端"""
    while True:
        try:
            socketio.sleep(5)
            data = collector.get_dashboard_data()
            socketio.emit('dashboard_update', data)
        except Exception as e:
            print(f"推送数据失败: {e}")

@app.route('/')
def index():
    """监控面板首页 - 自动检测设备类型"""
    user_agent = request.headers.get('User-Agent', '').lower()
    is_mobile = any(device in user_agent for device in ['mobile', 'android', 'iphone', 'ipad', 'wechat'])
    
    if is_mobile:
        return render_template('mobile.html')
    return render_template('dashboard.html')


@app.route('/mobile')
def mobile():
    """手机端监控面板"""
    return render_template('mobile.html')


@app.route('/desktop')
def desktop():
    """桌面端监控面板"""
    return render_template('dashboard.html')


@app.route('/api/dashboard')
def api_dashboard():
    """仪表盘数据 API"""
    return jsonify(collector.get_dashboard_data())


@app.route('/api/tasks')
def api_tasks():
    """任务列表 API"""
    with sqlite3.connect(collector.db_path) as conn:
        conn.row_factory = sqlite3.Row
        tasks = conn.execute('''
            SELECT * FROM task_stats 
            ORDER BY last_run_at DESC
        ''').fetchall()
    return jsonify([dict(row) for row in tasks])


@app.route('/api/executions/<task_id>')
def api_executions(task_id):
    """任务执行历史 API"""
    with sqlite3.connect(collector.db_path) as conn:
        conn.row_factory = sqlite3.Row
        executions = conn.execute('''
            SELECT * FROM task_executions 
            WHERE task_id = ?
            ORDER BY started_at DESC
            LIMIT 50
        ''', (task_id,)).fetchall()
    return jsonify([dict(row) for row in executions])


@app.route('/api/stats')
def api_stats():
    """统计图表数据 API"""
    with sqlite3.connect(collector.db_path) as conn:
        conn.row_factory = sqlite3.Row
        
        # 7天成功率
        weekly = conn.execute('''
            SELECT 
                date(started_at) as date,
                COUNT(*) as total,
                SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as success
            FROM task_executions
            WHERE started_at > datetime('now', '-7 days')
            GROUP BY date(started_at)
            ORDER BY date
        ''').fetchall()
        
        # 任务类型分布
        task_types = conn.execute('''
            SELECT status, COUNT(*) as count
            FROM task_executions
            WHERE started_at > datetime('now', '-24 hours')
            GROUP BY status
        ''').fetchall()
        
    return jsonify({
        'weekly': [dict(row) for row in weekly],
        'task_types': [dict(row) for row in task_types]
    })


@socketio.on('connect')
def handle_connect():
    """客户端连接"""
    print(f"客户端已连接")
    emit('dashboard_update', collector.get_dashboard_data())


@socketio.on('disconnect')
def handle_disconnect():
    """客户端断开"""
    print(f"客户端已断开")


@socketio.on('request_update')
def handle_request_update():
    """客户端请求立即更新"""
    emit('dashboard_update', collector.get_dashboard_data())


if __name__ == '__main__':
    import sqlite3
    
    print("=" * 50)
    print("  任务执行实时监控面板")
    print("=" * 50)
    print(f"\n🌐 Web 界面: http://localhost:5000")
    print(f"📱 手机版本: http://localhost:5000/mobile")
    print(f"💻 桌面版本: http://localhost:5000/desktop")
    print(f"\nAPI 接口:")
    print(f"  - GET /api/dashboard")
    print(f"  - GET /api/tasks")
    print(f"  - GET /api/executions/<task_id>")
    print(f"  - GET /api/stats")
    print("\n" + "=" * 50)
    
    # 启动后台推送线程
    socketio.start_background_task(background_push)
    
    # 启动服务器
    socketio.run(app, host='0.0.0.0', port=5000, debug=False, allow_unsafe_werkzeug=True)
