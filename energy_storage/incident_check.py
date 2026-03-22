#!/usr/bin/env python3
"""
故障自动检查脚本
每周运行，检查是否有重复发生的故障
"""

import sys
sys.path.insert(0, '/root/.openclaw/workspace/energy_storage')

from incident_manager import IncidentManager
from datetime import datetime

def main():
    print("=" * 60)
    print("🔍 故障重复性检查")
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    manager = IncidentManager()
    
    # 检查重复故障
    recurring = manager.check_recurring_issues()
    
    if recurring:
        print(f"\n⚠️  发现 {len(recurring)} 个重复故障类型:\n")
        for r in recurring:
            print(f"  【{r['title'][:50]}...】")
            print(f"     发生次数: {r['count']} 次")
            print(f"     首次: {r['incidents'][0]['timestamp'][:10]}")
            print(f"     最近: {r['incidents'][-1]['timestamp'][:10]}")
            
            # 检查是否已修复但又复发
            statuses = [inc['status'] for inc in r['incidents']]
            if 'fixed' in statuses and 'recurred' in statuses:
                print(f"     ⚠️ 警告：已标记为修复但再次复发！")
            print()
        
        # 返回非0状态码，方便外部监控
        return 1
    else:
        print("\n✅ 过去30天内无重复故障")
        print("\n📊 故障统计:")
        print(f"   总记录数: {len(manager.incidents)}")
        
        # 统计本周新增
        from datetime import timedelta
        cutoff = datetime.now() - timedelta(days=7)
        weekly = [inc for inc in manager.incidents 
                  if datetime.fromisoformat(inc['timestamp']) >= cutoff]
        print(f"   本周新增: {len(weekly)}")
        
        return 0

if __name__ == "__main__":
    exit(main())
