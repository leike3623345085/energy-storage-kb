#!/usr/bin/env python3
"""
全局任务健康检查系统
检查所有定时任务状态，自动修复常见问题，发送告警通知
"""

import json
import subprocess
import re
import sys
from datetime import datetime
from pathlib import Path

# 配置
WORKSPACE = Path("/root/.openclaw/workspace")
CRON_JOBS_FILE = Path("/root/.openclaw/cron/jobs.json")
LOG_FILE = WORKSPACE / "logs" / "health_check.log"
STATE_FILE = WORKSPACE / "logs" / "health_check_state.json"

# 导入企业微信推送
sys.path.insert(0, str(WORKSPACE / "energy_storage"))
try:
    from wechat_bot import send_markdown, send_text
    WECHAT_AVAILABLE = True
except ImportError:
    WECHAT_AVAILABLE = False

class TaskHealthChecker:
    """任务健康检查器"""
    
    def __init__(self):
        self.issues = []
        self.fixed = []
        self.state = self._load_state()
        
    def _load_state(self):
        """加载状态"""
        if STATE_FILE.exists():
            with open(STATE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {
            "last_check": None,
            "error_counts": {},
            "fixed_count": 0
        }
    
    def _save_state(self):
        """保存状态"""
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(STATE_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.state, f, ensure_ascii=False, indent=2)
    
    def log(self, message):
        """记录日志"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_msg = f"[{timestamp}] {message}"
        print(log_msg)
        
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(log_msg + "\n")
    
    def get_cron_jobs(self):
        """获取所有定时任务"""
        try:
            result = subprocess.run(
                ["openclaw", "cron", "list"],
                capture_output=True,
                text=True,
                timeout=30
            )
            # 解析输出
            jobs = []
            for line in result.stdout.split('\n'):
                if not line.strip() or line.startswith('│') or line.startswith('├') or line.startswith('─'):
                    continue
                # 解析: ID  Name  Schedule  Next  Last  Status  Target  Agent
                parts = line.split()
                if len(parts) >= 8:
                    jobs.append({
                        "id": parts[0],
                        "name": parts[1],
                        "schedule": parts[2],
                        "status": parts[6] if len(parts) > 6 else "unknown"
                    })
            return jobs
        except Exception as e:
            self.log(f"❌ 获取定时任务失败: {e}")
            return []
    
    def get_job_details(self, job_id):
        """获取任务详情"""
        try:
            if CRON_JOBS_FILE.exists():
                with open(CRON_JOBS_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for job in data.get('jobs', []):
                        if job.get('id') == job_id:
                            return job
            return None
        except Exception as e:
            self.log(f"❌ 获取任务详情失败: {e}")
            return None
    
    def check_task_status(self, job):
        """检查单个任务状态"""
        job_id = job.get('id')
        job_name = job.get('name', 'Unknown')
        status = job.get('status', 'unknown')
        
        details = self.get_job_details(job_id)
        if not details:
            return
        
        state = details.get('state', {})
        last_status = state.get('lastStatus', 'unknown')
        consecutive_errors = state.get('consecutiveErrors', 0)
        last_error = state.get('lastError', '')
        
        # 检查错误状态
        if last_status == 'error' or consecutive_errors > 0:
            issue = {
                "id": job_id,
                "name": job_name,
                "type": "error",
                "consecutive_errors": consecutive_errors,
                "last_error": last_error,
                "details": details
            }
            self.issues.append(issue)
            self.log(f"⚠️ 任务异常: {job_name} (连续错误: {consecutive_errors})")
            
            # 尝试自动修复
            self.try_auto_fix(issue)
    
    def try_auto_fix(self, issue):
        """尝试自动修复问题"""
        job_id = issue['id']
        job_name = issue['name']
        last_error = issue.get('last_error', '')
        details = issue.get('details', {})
        
        fix_applied = False
        
        # 修复1: 超时问题
        if 'timed out' in last_error.lower() or 'timeout' in last_error.lower():
            payload = details.get('payload', {})
            current_timeout = payload.get('timeoutSeconds', 60)
            
            if current_timeout < 300:
                new_timeout = min(current_timeout * 2, 300)
                self.log(f"  🔧 尝试修复超时: {current_timeout}s -> {new_timeout}s")
                
                try:
                    subprocess.run(
                        ['openclaw', 'cron', 'update', job_id, 
                         '--patch', json.dumps({"payload": {**payload, "timeoutSeconds": new_timeout}})],
                        capture_output=True,
                        timeout=10
                    )
                    fix_applied = True
                    self.fixed.append({
                        "job": job_name,
                        "fix": f"超时调整: {current_timeout}s -> {new_timeout}s"
                    })
                except Exception as e:
                    self.log(f"  ❌ 修复失败: {e}")
        
        # 修复2: 标记为idle的任务检查
        if issue.get('status') == 'idle':
            self.log(f"  ℹ️ 任务处于idle状态，检查是否需要触发")
        
        if fix_applied:
            self.state['fixed_count'] += 1
    
    def generate_report(self):
        """生成检查报告"""
        report = []
        report.append("=" * 60)
        report.append("📊 任务健康检查报告")
        report.append(f"⏰ 检查时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("=" * 60)
        
        if not self.issues:
            report.append("\n✅ 所有任务运行正常")
        else:
            report.append(f"\n⚠️ 发现 {len(self.issues)} 个问题:")
            for issue in self.issues:
                report.append(f"\n  📌 {issue['name']}")
                report.append(f"     状态: {issue['type']}")
                report.append(f"     连续错误: {issue['consecutive_errors']} 次")
                if issue.get('last_error'):
                    report.append(f"     最后错误: {issue['last_error'][:100]}...")
        
        if self.fixed:
            report.append(f"\n🔧 自动修复 {len(self.fixed)} 个问题:")
            for fix in self.fixed:
                report.append(f"  ✅ {fix['job']}: {fix['fix']}")
        
        report.append("\n" + "=" * 60)
        return '\n'.join(report)
    
    def send_notification(self, report):
        """发送通知 - 企业微信"""
        # 保存到文件
        report_file = WORKSPACE / "logs" / f"health_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)
        self.log(f"📄 报告已保存: {report_file}")
        
        # 发送企业微信通知
        if not WECHAT_AVAILABLE:
            self.log("⚠️ 企业微信模块不可用")
            return
        
        # 构建Markdown消息
        if self.issues:
            status_emoji = "⚠️"
            status_text = f"发现 {len(self.issues)} 个问题"
        else:
            status_emoji = "✅"
            status_text = "所有任务运行正常"
        
        markdown = f"""## {status_emoji} 任务健康检查

**检查时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**检查任务数**: {len(self.get_cron_jobs())}

---

### 检查结果: {status_text}

"""
        
        if self.issues:
            markdown += "**异常任务详情**:\n\n"
            for issue in self.issues:
                markdown += f"• **{issue['name']}**\n"
                markdown += f"  - 连续错误: {issue['consecutive_errors']} 次\n"
                if issue.get('last_error'):
                    error_short = issue['last_error'][:60] + "..." if len(issue['last_error']) > 60 else issue['last_error']
                    markdown += f"  - 错误信息: {error_short}\n"
                markdown += "\n"
        
        if self.fixed:
            markdown += "**自动修复**:\n\n"
            for fix in self.fixed:
                markdown += f"✅ {fix['job']}: {fix['fix']}\n"
            markdown += "\n"
        
        markdown += "---\n> 自动发送 | 任务健康检查系统"
        
        try:
            result = send_markdown(markdown)
            if result:
                self.log("✅ 企业微信通知已发送")
            else:
                self.log("❌ 企业微信通知发送失败")
        except Exception as e:
            self.log(f"❌ 企业微信推送异常: {e}")
    
    def run(self):
        """运行健康检查"""
        self.log("=" * 60)
        self.log("🔍 全局任务健康检查启动")
        self.log("=" * 60)
        
        # 获取所有任务
        jobs = self.get_cron_jobs()
        self.log(f"📋 发现 {len(jobs)} 个定时任务")
        
        # 检查每个任务
        for job in jobs:
            self.check_task_status(job)
        
        # 生成报告
        report = self.generate_report()
        
        # 保存状态
        self.state['last_check'] = datetime.now().isoformat()
        self._save_state()
        
        # 发送通知
        self.send_notification(report)
        
        self.log("=" * 60)
        self.log("健康检查完成")
        self.log("=" * 60)
        
        return len(self.issues) == 0


def main():
    """主入口"""
    checker = TaskHealthChecker()
    success = checker.run()
    return 0 if success else 1


if __name__ == "__main__":
    exit(main())
