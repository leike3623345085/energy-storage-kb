#!/usr/bin/env python3
"""
储能爬虫全自动闭环系统
主控制器 - 集成验证、回滚、修复
"""
import json
import sys
from datetime import datetime
from pathlib import Path

WORKSPACE = Path("/root/.openclaw/workspace/energy_storage")
LOG_FILE = WORKSPACE / "logs/full_loop.log"

def ensure_dirs():
    (WORKSPACE / "logs").mkdir(parents=True, exist_ok=True)

def log_event(event_type, data):
    """记录闭环日志"""
    entry = {
        "timestamp": datetime.now().isoformat(),
        "event": event_type,
        "data": data
    }
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

class FullLoopController:
    """全自动闭环控制器"""
    
    def __init__(self):
        self.state = "idle"
        ensure_dirs()
    
    def deploy(self, deploy_type="auto"):
        """
        全自动部署流程
        
        1. 创建备份
        2. 运行验证
        3. 如果通过 → 部署完成
        4. 如果失败 → 回滚 → 自动修复 → 重新验证
        """
        print("=" * 60)
        print("储能爬虫全自动闭环部署")
        print("=" * 60)
        
        # 步骤1: 创建备份
        print("\n📦 步骤1: 创建备份...")
        from rollback_system import create_backup
        backup_tag = create_backup("pre_deploy")
        log_event("backup_created", {"tag": backup_tag})
        
        # 步骤2: 运行验证
        print("\n🔍 步骤2: 运行验证套件...")
        from validation_suite import validate_crawler
        validation_report = validate_crawler(trials=3)
        log_event("validation_run", validation_report)
        
        if validation_report["passed"]:
            print("\n✅ 验证通过，部署完成")
            self.state = "deployed"
            log_event("deploy_success", validation_report["summary"])
            return {
                "success": True,
                "state": "deployed",
                "validation": validation_report["summary"]
            }
        
        # 验证失败，进入修复流程
        print("\n❌ 验证失败，启动自动修复...")
        return self._repair_and_retry(validation_report, backup_tag)
    
    def _repair_and_retry(self, validation_report, backup_tag, max_retries=3):
        """修复并重试"""
        from auto_repair import auto_repair, diagnose_failure
        from validation_suite import validate_crawler
        
        for attempt in range(max_retries):
            print(f"\n🔧 修复尝试 {attempt + 1}/{max_retries}")
            
            # 诊断失败原因
            failure_type, error_msg = diagnose_failure(validation_report)
            log_event("failure_diagnosed", {"type": failure_type, "msg": error_msg})
            
            # 步骤3: 回滚到稳定版本（如果是代码问题）
            if attempt == 0:
                print("📦 步骤3: 回滚到稳定版本...")
                from rollback_system import rollback
                rollback_result = rollback(backup_tag)
                log_event("rollback", rollback_result)
            
            # 步骤4: 自动修复
            print("\n🔧 步骤4: 应用修复策略...")
            repair_result = auto_repair(failure_type, error_msg)
            log_event("auto_repair", repair_result)
            
            if not repair_result["repaired"]:
                print("❌ 自动修复失败")
                break
            
            # 步骤5: 重新验证
            print("\n🔍 步骤5: 重新验证...")
            validation_report = validate_crawler(trials=2)  # 修复后用更少的次数
            log_event("re_validation", validation_report)
            
            if validation_report["passed"]:
                print("\n✅ 修复成功，验证通过，部署完成")
                self.state = "deployed_after_repair"
                log_event("deploy_success_after_repair", {
                    "attempts": attempt + 1,
                    "validation": validation_report["summary"]
                })
                return {
                    "success": True,
                    "state": "deployed_after_repair",
                    "attempts": attempt + 1,
                    "validation": validation_report["summary"]
                }
            
            print(f"⚠️ 修复后仍失败，准备下一次尝试...")
        
        # 所有尝试都失败
        print("\n❌ 所有修复尝试均失败，需要人工介入")
        self.state = "failed"
        log_event("deploy_failed", {"attempts": max_retries})
        return {
            "success": False,
            "state": "failed",
            "message": "所有自动修复策略均失败，需要人工介入"
        }
    
    def health_check(self):
        """健康检查"""
        print("\n🏥 健康检查...")
        
        from validation_suite import run_crawler_test
        result = run_crawler_test()
        
        if result["return_code"] == 0 and result["data_count"] > 50:
            print("✅ 健康")
            return {"healthy": True, "data_count": result["data_count"]}
        else:
            print("⚠️ 异常，触发自动修复...")
            return self._emergency_repair(result)
    
    def _emergency_repair(self, failure_result):
        """紧急修复（运行时发现问题）"""
        from auto_repair import auto_repair
        from validation_suite import validate_crawler
        
        error_msg = failure_result.get("stderr", "execution failed")
        repair_result = auto_repair("runtime_failure", error_msg)
        
        if repair_result["repaired"]:
            # 修复后验证
            validation = validate_crawler(trials=1)
            if validation["passed"]:
                return {"healthy": True, "repaired": True}
        
        return {"healthy": False, "repaired": False}

def main():
    """主函数"""
    controller = FullLoopController()
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "deploy":
            result = controller.deploy()
            print("\n" + "=" * 60)
            print("部署结果:")
            print(json.dumps(result, ensure_ascii=False, indent=2))
            
        elif command == "health":
            result = controller.health_check()
            print(json.dumps(result, ensure_ascii=False, indent=2))
            
        elif command == "status":
            print(f"当前状态: {controller.state}")
            
        else:
            print("Usage: python3 full_loop_controller.py [deploy|health|status]")
    else:
        # 默认运行部署流程
        result = controller.deploy()
        print("\n" + "=" * 60)
        print("部署结果:")
        print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
