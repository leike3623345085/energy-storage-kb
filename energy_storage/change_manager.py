#!/usr/bin/env python3
"""
变更管理检查清单 (Change Management Checklist)
任何升级变更前必须完成的检查项
"""

from datetime import datetime
from pathlib import Path
import json

CHECKLIST_FILE = Path(__file__).parent / "data" / "change_records.jsonl"

CHANGE_CHECKLIST = {
    "before_change": [
        {
            "item": "备份当前版本",
            "description": "代码、配置、数据全部备份",
            "verify_cmd": "git status && git log -1",
            "required": True
        },
        {
            "item": "创建回退方案",
            "description": "明确的回退步骤和触发条件",
            "verify_cmd": "cat ROLLBACK.md 或文档中存在回退章节",
            "required": True
        },
        {
            "item": "数据兼容性检查",
            "description": "新旧版本数据格式是否兼容",
            "verify_cmd": "检查新旧版本的数据源、API、存储格式",
            "required": True
        },
        {
            "item": "记录变更计划",
            "description": "变更内容、影响范围、预计时间",
            "verify_cmd": "incident_manager.py --record-change",
            "required": True
        }
    ],
    "during_change": [
        {
            "item": "灰度/分段发布",
            "description": "先小范围验证，再全量发布",
            "verify_cmd": "检查是否有 --test 或 --dry-run 参数",
            "required": False
        },
        {
            "item": "实时监控",
            "description": "观察日志、指标、错误率",
            "verify_cmd": "tail -f logs/",
            "required": True
        }
    ],
    "after_change": [
        {
            "item": "功能验证",
            "description": "核心功能是否正常",
            "verify_cmd": "运行测试脚本或手动验证",
            "required": True
        },
        {
            "item": "数据通路验证",
            "description": "输入→处理→输出全流程验证",
            "verify_cmd": "检查关键数据文件是否生成、内容是否完整",
            "required": True
        },
        {
            "item": "输出质量检查",
            "description": "格式正确且内容非空",
            "verify_cmd": "检查输出文件大小、关键字段存在性",
            "required": True
        },
        {
            "item": "监控告警检查",
            "description": "无异常告警",
            "verify_cmd": "检查日志中的 ERROR/WARNING",
            "required": True
        },
        {
            "item": "记录变更结果",
            "description": "实际结果、问题、解决方案",
            "verify_cmd": "更新变更记录为完成或回退",
            "required": True
        }
    ]
}


class ChangeManager:
    """变更管理器"""
    
    def __init__(self):
        CHECKLIST_FILE.parent.mkdir(parents=True, exist_ok=True)
        self.records = self._load_records()
    
    def _load_records(self):
        """加载变更记录"""
        records = []
        if CHECKLIST_FILE.exists():
            with open(CHECKLIST_FILE, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        records.append(json.loads(line.strip()))
                    except:
                        continue
        return records
    
    def create_change_record(self, title: str, component: str, change_type: str, 
                           description: str, rollback_plan: str) -> dict:
        """创建变更记录"""
        record = {
            "id": f"CHG-{datetime.now().strftime('%Y%m%d')}-{len(self.records)+1:03d}",
            "timestamp": datetime.now().isoformat(),
            "title": title,
            "component": component,
            "change_type": change_type,  # upgrade/feature/fix/config
            "description": description,
            "rollback_plan": rollback_plan,
            "status": "planned",  # planned/in_progress/completed/rolled_back
            "checklist": {k: {item["item"]: False for item in v} 
                         for k, v in CHANGE_CHECKLIST.items()},
            "result": None,
            "incident_id": None  # 关联的故障ID（如有）
        }
        return record
    
    def print_checklist(self):
        """打印检查清单"""
        print("=" * 70)
        print("🔧 变更管理检查清单")
        print("=" * 70)
        
        for phase, items in CHANGE_CHECKLIST.items():
            phase_name = {
                "before_change": "变更前（必须完成）",
                "during_change": "变更中",
                "after_change": "变更后（必须完成）"
            }.get(phase, phase)
            
            print(f"\n📋 {phase_name}")
            print("-" * 70)
            
            for item in items:
                req = "【必须】" if item["required"] else "【建议】"
                print(f"  {req} {item['item']}")
                print(f"      说明: {item['description']}")
                print(f"      验证: {item['verify_cmd']}")
                print()
    
    def verify_change(self, record_id: str) -> bool:
        """
        验证变更是否满足所有检查项
        返回是否可以通过
        """
        # 查找记录
        record = None
        for r in self.records:
            if r["id"] == record_id:
                record = r
                break
        
        if not record:
            print(f"❌ 未找到变更记录: {record_id}")
            return False
        
        print(f"\n🔍 验证变更: {record['title']}")
        print("=" * 70)
        
        all_passed = True
        for phase, items in record["checklist"].items():
            phase_name = {
                "before_change": "变更前",
                "during_change": "变更中", 
                "after_change": "变更后"
            }.get(phase, phase)
            
            print(f"\n{phase_name}:")
            for item_name, checked in items.items():
                # 检查是否必须
                is_required = any(
                    i["item"] == item_name and i["required"]
                    for i in CHANGE_CHECKLIST[phase]
                )
                
                status = "✅" if checked else "❌"
                req_mark = "【必须】" if is_required else ""
                
                if is_required and not checked:
                    all_passed = False
                    status = "❌"
                
                print(f"  {status} {req_mark}{item_name}")
        
        print("\n" + "=" * 70)
        if all_passed:
            print("✅ 所有必须检查项已通过，变更可以上线")
        else:
            print("❌ 有必须检查项未完成，请勿上线")
        
        return all_passed


def main():
    """CLI入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description='变更管理检查清单')
    parser.add_argument('--list', action='store_true', help='打印检查清单')
    parser.add_argument('--create', action='store_true', help='创建变更记录')
    parser.add_argument('--verify', help='验证变更记录ID')
    parser.add_argument('--title', help='变更标题')
    parser.add_argument('--component', default='energy-storage', help='组件名')
    parser.add_argument('--type', default='upgrade', help='变更类型')
    
    args = parser.parse_args()
    
    manager = ChangeManager()
    
    if args.list:
        manager.print_checklist()
    elif args.create:
        if not args.title:
            print("错误: --create 需要 --title")
            return 1
        
        print("=" * 70)
        print("创建变更记录")
        print("=" * 70)
        
        description = input("\n变更描述: ").strip()
        rollback_plan = input("回退方案: ").strip()
        
        record = manager.create_change_record(
            title=args.title,
            component=args.component,
            change_type=args.type,
            description=description,
            rollback_plan=rollback_plan
        )
        
        # 保存
        with open(CHECKLIST_FILE, 'a', encoding='utf-8') as f:
            f.write(json.dumps(record, ensure_ascii=False) + '\n')
        
        print(f"\n✅ 变更记录已创建: {record['id']}")
        print(f"\n⚠️  请严格按照检查清单执行变更！")
        print(f"   完成后运行: python3 change_manager.py --verify {record['id']}")
        
    elif args.verify:
        manager.verify_change(args.verify)
    else:
        manager.print_checklist()
    
    return 0


if __name__ == "__main__":
    exit(main())
