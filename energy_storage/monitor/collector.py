#!/usr/bin/env python3
"""
任务执行实时监控面板 - 数据收集器
收集 OpenClaw Cron 任务执行状态
"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import subprocess
import threading
import time


class TaskMonitorCollector:
    """任务监控数据收集器"""
    
    def __init__(self, db_path: str = "data/task_monitor.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.init_db()
    
    def init_db(self):
        """初始化数据库"""
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript('''
                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    schedule TEXT,
                    enabled INTEGER DEFAULT 1,
                    created_at TEXT,
                    updated_at TEXT
                );
                
                CREATE TABLE IF NOT EXISTS task_executions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT,
                    task_name TEXT,
                    started_at TEXT,
                    completed_at TEXT,
                    duration_ms INTEGER,
                    status TEXT,  -- success, error, timeout, running
                    error_message TEXT,
                    output_snippet TEXT,
                    FOREIGN KEY (task_id) REFERENCES tasks(id)
                );
                
                CREATE TABLE IF NOT EXISTS task_stats (
                    task_id TEXT PRIMARY KEY,
                    total_runs INTEGER DEFAULT 0,
                    success_runs INTEGER DEFAULT 0,
                    error_runs INTEGER DEFAULT 0,
                    last_run_at TEXT,
                    last_status TEXT,
                    avg_duration_ms INTEGER DEFAULT 0,
                    consecutive_errors INTEGER DEFAULT 0
                );
                
                CREATE INDEX IF NOT EXISTS idx_executions_time 
                    ON task_executions(started_at);
                CREATE INDEX IF NOT EXISTS idx_executions_status 
                    ON task_executions(status);
            ''')
    
    def sync_cron_jobs(self):
        """从 OpenClaw 同步定时任务列表"""
        try:
            result = subprocess.run(
                ['openclaw', 'cron', 'list'],
                capture_output=True,
                text=True,
                timeout=30
            )
            jobs = json.loads(result.stdout)
            
            with sqlite3.connect(self.db_path) as conn:
                for job in jobs:
                    conn.execute('''
                        INSERT OR REPLACE INTO tasks 
                        (id, name, schedule, enabled, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (
                        job['id'],
                        job.get('name', 'Unnamed'),
                        json.dumps(job.get('schedule', {})),
                        1 if job.get('enabled', True) else 0,
                        job.get('createdAtMs'),
                        job.get('updatedAtMs')
                    ))
            
            return len(jobs)
        except Exception as e:
            print(f"同步任务列表失败: {e}")
            return 0
    
    def record_execution_start(self, task_id: str, task_name: str):
        """记录任务开始执行"""
        now = datetime.now().isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            # 记录为 running 状态
            conn.execute('''
                INSERT INTO task_executions 
                (task_id, task_name, started_at, completed_at, duration_ms, status)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (task_id, task_name, now, None, 0, 'running'))
            
            # 更新统计为 running
            conn.execute('''
                INSERT INTO task_stats (task_id, last_run_at, last_status)
                VALUES (?, ?, ?)
                ON CONFLICT(task_id) DO UPDATE SET
                    last_run_at = excluded.last_run_at,
                    last_status = excluded.last_status
            ''', (task_id, now, 'running'))
    
    def record_execution(self, task_id: str, task_name: str,
                         status: str, duration_ms: int = 0,
                         error_message: str = None,
                         output_snippet: str = None):
        """记录任务执行完成"""
        now = datetime.now().isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            # 记录执行
            conn.execute('''
                INSERT INTO task_executions 
                (task_id, task_name, started_at, completed_at, duration_ms, 
                 status, error_message, output_snippet)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (task_id, task_name, now, now, duration_ms,
                  status, error_message, output_snippet))
            
            # 更新统计
            conn.execute('''
                INSERT INTO task_stats (task_id, total_runs, success_runs, 
                    error_runs, last_run_at, last_status, consecutive_errors)
                VALUES (?, 1, ?, ?, ?, ?, ?)
                ON CONFLICT(task_id) DO UPDATE SET
                    total_runs = total_runs + 1,
                    success_runs = success_runs + excluded.success_runs,
                    error_runs = error_runs + excluded.error_runs,
                    last_run_at = excluded.last_run_at,
                    last_status = excluded.last_status,
                    consecutive_errors = CASE 
                        WHEN excluded.last_status = 'error' 
                        THEN consecutive_errors + 1 
                        ELSE 0 
                    END
            ''', (task_id, 
                  1 if status == 'success' else 0,
                  1 if status == 'error' else 0,
                  now, status,
                  0 if status == 'success' else 1))
    
    def get_running_tasks(self) -> List[Dict]:
        """获取正在执行的任务"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            running = conn.execute('''
                SELECT 
                    task_id,
                    task_name,
                    started_at,
                    (julianday('now') - julianday(started_at)) * 24 * 60 * 60 * 1000 as duration_ms
                FROM task_executions 
                WHERE status = 'running'
                AND started_at > datetime('now', '-1 hour')
                ORDER BY started_at DESC
            ''').fetchall()
            
            return [dict(row) for row in running]
    
    def get_dashboard_data(self) -> Dict:
        """获取仪表盘数据"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            # 总体统计
            total_tasks = conn.execute(
                'SELECT COUNT(*) FROM tasks WHERE enabled = 1'
            ).fetchone()[0]
            
            # 今日执行统计
            today = datetime.now().strftime('%Y-%m-%d')
            today_stats = conn.execute('''
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as success,
                    SUM(CASE WHEN status = 'error' THEN 1 ELSE 0 END) as error
                FROM task_executions 
                WHERE date(started_at) = date('now', 'localtime')
            ''').fetchone()
            
            # 最近24小时执行趋势（按小时）
            hourly_trend = conn.execute('''
                SELECT 
                    strftime('%H', started_at) as hour,
                    status,
                    COUNT(*) as count
                FROM task_executions 
                WHERE started_at >= datetime('now', '-24 hours')
                GROUP BY hour, status
                ORDER BY hour
            ''').fetchall()
            
            # 任务列表（带状态）
            tasks = conn.execute('''
                SELECT 
                    t.id,
                    t.name,
                    t.enabled,
                    COALESCE(s.last_run_at, '从未执行') as last_run,
                    COALESCE(s.last_status, 'unknown') as last_status,
                    COALESCE(s.total_runs, 0) as total_runs,
                    COALESCE(s.consecutive_errors, 0) as consecutive_errors
                FROM tasks t
                LEFT JOIN task_stats s ON t.id = s.task_id
                ORDER BY t.enabled DESC, s.last_run_at DESC
            ''').fetchall()
            
            # 最近错误
            recent_errors = conn.execute('''
                SELECT task_name, error_message, started_at
                FROM task_executions 
                WHERE status = 'error' 
                ORDER BY started_at DESC 
                LIMIT 5
            ''').fetchall()
            
            # 获取正在执行的任务
            running_tasks = self.get_running_tasks()
            
            return {
                'total_tasks': total_tasks,
                'today_executions': {
                    'total': today_stats['total'] or 0,
                    'success': today_stats['success'] or 0,
                    'error': today_stats['error'] or 0
                },
                'hourly_trend': [dict(row) for row in hourly_trend],
                'tasks': [dict(row) for row in tasks],
                'recent_errors': [dict(row) for row in recent_errors],
                'running_tasks': running_tasks,
                'updated_at': datetime.now().isoformat()
            }


def start_monitoring(interval: int = 60):
    """启动监控（在后台线程中）"""
    collector = TaskMonitorCollector()
    
    def monitor_loop():
        while True:
            try:
                # 同步任务列表
                collector.sync_cron_jobs()
                print(f"[{datetime.now()}] 任务列表同步完成")
            except Exception as e:
                print(f"监控循环错误: {e}")
            
            time.sleep(interval)
    
    thread = threading.Thread(target=monitor_loop, daemon=True)
    thread.start()
    return collector


if __name__ == '__main__':
    # 测试
    collector = TaskMonitorCollector()
    collector.sync_cron_jobs()
    
    # 模拟记录一些执行
    collector.record_execution(
        'test-1', '测试任务', 'success', 5000,
        output_snippet='任务执行成功'
    )
    
    data = collector.get_dashboard_data()
    print(json.dumps(data, indent=2, ensure_ascii=False))
