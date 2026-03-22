#!/usr/bin/env python3
"""
故障记录与教训管理工具
自动记录故障、检查重复、生成教训报告
"""

import json
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# 配置
MEMORY_DIR = Path("/root/.openclaw/workspace/memory")
LESSONS_DIR = MEMORY_DIR / "lessons"
INCIDENTS_FILE = LESSONS_DIR / "incidents.jsonl"
CHECK_INTERVAL_DAYS = 30  # 检查30天内的重复故障

class IncidentManager:
    """故障管理器"""
    
    def __init__(self):
        LESSONS_DIR.mkdir(parents=True, exist_ok=True)
        self.incidents = self._load_incidents()
    
    def _load_incidents(self) -> List[Dict]:
        """加载历史故障记录"""
        incidents = []
        if INCIDENTS_FILE.exists():
            with open(INCIDENTS_FILE, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        incidents.append(json.loads(line.strip()))
                    except:
                        continue
        return incidents
    
    def _save_incident(self, incident: Dict):
        """保存单条故障记录"""
        with open(INCIDENTS_FILE, 'a', encoding='utf-8') as f:
            f.write(json.dumps(incident, ensure_ascii=False) + '\n')
    
    def _generate_signature(self, title: str, root_causes: List[str]) -> str:
        """生成故障签名（用于识别同类故障）"""
        # 提取关键词，忽略日期等变化部分
        content = title.lower() + ' '.join(root_causes).lower()
        # 移除常见变化词
        for word in ['202', '03-', '02-', '01-', '日报', '今日', '昨天']:
            content = content.replace(word, '')
        return hashlib.md5(content.encode()).hexdigest()[:12]
    
    def record_incident(
        self,
        project: str,
        title: str,
        symptoms: str,
        root_causes: List[str],
        fix_actions: List[str],
        lessons: List[str],
        severity: str = "medium"  # low/medium/high/critical
    ) -> Dict:
        """
        记录新故障
        
        Args:
            project: 项目名称，如 "energy-storage"
            title: 故障标题
            symptoms: 现象描述
            root_causes: 根因列表
            fix_actions: 修复措施列表
            lessons: 经验教训列表
            severity: 严重程度
        """
        incident = {
            "id": f"INC-{datetime.now().strftime('%Y%m%d')}-{len(self.incidents)+1:03d}",
            "timestamp": datetime.now().isoformat(),
            "project": project,
            "title": title,
            "symptoms": symptoms,
            "root_causes": root_causes,
            "fix_actions": fix_actions,
            "lessons": lessons,
            "severity": severity,
            "signature": self._generate_signature(title, root_causes),
            "status": "recorded"  # recorded/fixed/verified/recurred
        }
        
        # 检查是否重复
        similar = self._find_similar_incidents(incident["signature"])
        if similar:
            incident["similar_incidents"] = similar
            incident["status"] = "recurred"
            print(f"⚠️  警告：发现 {len(similar)} 个同类历史故障！")
            for s in similar:
                print(f"   - {s['id']}: {s['title'][:40]}... ({s['timestamp'][:10]})")
        
        # 保存
        self._save_incident(incident)
        self.incidents.append(incident)
        
        # 同步写入 lessons/{project}.md
        self._append_to_lessons_md(incident)
        
        return incident
    
    def _find_similar_incidents(self, signature: str) -> List[Dict]:
        """查找同类故障（30天内）"""
        cutoff = datetime.now() - timedelta(days=CHECK_INTERVAL_DAYS)
        similar = []
        
        for inc in self.incidents:
            inc_time = datetime.fromisoformat(inc["timestamp"])
            if inc_time < cutoff:
                continue
            if inc["signature"] == signature:
                similar.append(inc)
        
        return similar
    
    def _append_to_lessons_md(self, incident: Dict):
        """追加到 lessons/{project}.md"""
        lessons_file = LESSONS_DIR / f"{incident['project']}.md"
        
        # 构建内容
        content = f"""
## {incident['timestamp'][:10]}

### {incident['title']}
**问题**：{incident['symptoms']}
**严重程度**：{incident['severity']}
**根因**：
"""
        for cause in incident['root_causes']:
            content += f"- {cause}\n"
        
        content += "**修复**：\n"
        for fix in incident['fix_actions']:
            content += f"- {fix}\n"
        
        content += "**教训**：\n"
        for lesson in incident['lessons']:
            content += f"- {lesson}\n"
        
        if incident.get('similar_incidents'):
            content += f"**⚠️ 重复故障**：{len(incident['similar_incidents'])} 次历史发生\n"
        
        content += "---\n"
        
        # 写入文件（在文件头部插入）
        if lessons_file.exists():
            with open(lessons_file, 'r', encoding='utf-8') as f:
                existing = f.read()
            # 找到第一个 ## 日期 的位置，在其前插入
            insert_pos = existing.find('\n## ')
            if insert_pos == -1:
                insert_pos = len(existing)
            new_content = existing[:insert_pos] + content + existing[insert_pos:]
        else:
            new_content = f"# {incident['project']} 运维经验教训\n\n> 按时间倒序排列\n\n" + content
        
        with open(lessons_file, 'w', encoding='utf-8') as f:
            f.write(new_content)
    
    def check_recurring_issues(self) -> List[Dict]:
        """检查重复发生的故障"""
        cutoff = datetime.now() - timedelta(days=CHECK_INTERVAL_DAYS)
        signatures = {}
        
        for inc in self.incidents:
            inc_time = datetime.fromisoformat(inc["timestamp"])
            if inc_time < cutoff:
                continue
            
            sig = inc["signature"]
            if sig not in signatures:
                signatures[sig] = []
            signatures[sig].append(inc)
        
        # 找出重复2次以上的
        recurring = []
        for sig, incidents in signatures.items():
            if len(incidents) >= 2:
                recurring.append({
                    "signature": sig,
                    "count": len(incidents),
                    "title": incidents[0]["title"],
                    "incidents": incidents
                })
        
        return recurring
    
    def generate_weekly_report(self) -> str:
        """生成周度故障报告"""
        cutoff = datetime.now() - timedelta(days=7)
        weekly_incidents = [
            inc for inc in self.incidents
            if datetime.fromisoformat(inc["timestamp"]) >= cutoff
        ]
        
        report = f"""# 故障周度报告

**统计周期**：{cutoff.strftime('%Y-%m-%d')} 至 {datetime.now().strftime('%Y-%m-%d')}
**故障总数**：{len(weekly_incidents)}

## 新增故障

"""
        for inc in weekly_incidents:
            report += f"- [{inc['severity']}] {inc['title']} ({inc['timestamp'][:10]})\n"
        
        # 重复故障检查
        recurring = self.check_recurring_issues()
        if recurring:
            report += "\n## ⚠️ 重复故障警告\n\n"
            for r in recurring:
                report += f"- **{r['title'][:40]}...** 发生了 {r['count']} 次\n"
        
        return report


def main():
    """CLI入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description='故障记录与教训管理')
    parser.add_argument('--record', action='store_true', help='记录新故障')
    parser.add_argument('--check', action='store_true', help='检查重复故障')
    parser.add_argument('--report', action='store_true', help='生成周度报告')
    parser.add_argument('--project', default='energy-storage', help='项目名称')
    parser.add_argument('--title', help='故障标题')
    parser.add_argument('--symptoms', help='故障现象')
    parser.add_argument('--severity', default='medium', help='严重程度')
    
    args = parser.parse_args()
    
    manager = IncidentManager()
    
    if args.record:
        if not args.title or not args.symptoms:
            print("错误：--record 需要 --title 和 --symptoms")
            return 1
        
        # 交互式收集信息
        print("=" * 60)
        print("记录新故障")
        print("=" * 60)
        
        root_causes = []
        print("\n输入根因（每行一个，空行结束）：")
        while True:
            cause = input("  > ").strip()
            if not cause:
                break
            root_causes.append(cause)
        
        fix_actions = []
        print("\n输入修复措施（每行一个，空行结束）：")
        while True:
            fix = input("  > ").strip()
            if not fix:
                break
            fix_actions.append(fix)
        
        lessons = []
        print("\n输入经验教训（每行一个，空行结束）：")
        while True:
            lesson = input("  > ").strip()
            if not lesson:
                break
            lessons.append(lesson)
        
        incident = manager.record_incident(
            project=args.project,
            title=args.title,
            symptoms=args.symptoms,
            root_causes=root_causes,
            fix_actions=fix_actions,
            lessons=lessons,
            severity=args.severity
        )
        
        print(f"\n✅ 故障已记录: {incident['id']}")
        if incident.get('similar_incidents'):
            print(f"⚠️  这是该类故障第 {len(incident['similar_incidents'])+1} 次发生")
    
    elif args.check:
        recurring = manager.check_recurring_issues()
        if recurring:
            print("⚠️  发现重复故障：")
            for r in recurring:
                print(f"  - {r['title'][:40]}... ({r['count']} 次)")
        else:
            print("✅ 30天内无重复故障")
    
    elif args.report:
        report = manager.generate_weekly_report()
        print(report)
    
    else:
        parser.print_help()
    
    return 0


if __name__ == "__main__":
    exit(main())
