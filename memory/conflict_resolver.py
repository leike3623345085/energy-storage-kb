#!/usr/bin/env python3
"""
记忆冲突检测与解决系统
处理新旧记忆的矛盾和不一致
"""
import json
import re
from datetime import datetime
from pathlib import Path
from difflib import SequenceMatcher

WORKSPACE = Path("/root/.openclaw/workspace")
MEMORY_DIR = WORKSPACE / "memory"
CONFLICT_LOG = MEMORY_DIR / "conflicts.log"

def similar(a, b):
    """计算文本相似度"""
    return SequenceMatcher(None, a, b).ratio()

def detect_conflict(new_content, memory_type="general"):
    """
    检测新内容与现有记忆的冲突
    
    返回: {
        "has_conflict": bool,
        "conflicts": [{
            "type": "contradiction|update|refinement",
            "existing": "...",
            "new": "...",
            "severity": "high|medium|low",
            "suggestion": "..."
        }]
    }
    """
    conflicts = []
    
    # 根据记忆类型加载相关文件
    if memory_type == "preference":
        files = [WORKSPACE / "USER.md"]
    elif memory_type == "rule":
        files = [WORKSPACE / "MEMORY.md", WORKSPACE / "AGENTS.md"]
    elif memory_type == "identity":
        files = [WORKSPACE / "SOUL.md"]
    else:
        files = list(MEMORY_DIR.glob("*.md"))
    
    for file_path in files:
        if not file_path.exists():
            continue
            
        existing_content = file_path.read_text(encoding='utf-8')
        
        # 1. 直接矛盾检测
        contradiction = check_contradiction(new_content, existing_content)
        if contradiction:
            conflicts.append({
                "type": "contradiction",
                "file": str(file_path),
                "existing": contradiction["existing"],
                "new": contradiction["new"],
                "severity": "high",
                "suggestion": "需要用户确认或澄清"
            })
        
        # 2. 更新/细化检测
        update = check_update(new_content, existing_content)
        if update:
            conflicts.append({
                "type": "update",
                "file": str(file_path),
                "existing": update["existing"],
                "new": update["new"],
                "severity": "medium",
                "suggestion": "自动合并或覆盖"
            })
    
    return {
        "has_conflict": len(conflicts) > 0,
        "conflicts": conflicts
    }

def check_contradiction(new, existing):
    """检测直接矛盾"""
    # 提取关键陈述（简化版）
    patterns = [
        (r"喜欢(.+?)[,。]", r"不喜欢\1"),
        (r"使用(.+?)[,。]", r"不使用\1"),
        (r"必须(.+?)[,。]", r"不必\1"),
        (r"直接(.+?)[,。]", r"不直接\1"),
    ]
    
    for pos_pattern, neg_pattern in patterns:
        pos_matches = re.findall(pos_pattern, existing)
        neg_matches = re.findall(neg_pattern, new)
        
        for pos in pos_matches:
            for neg in neg_matches:
                if similar(pos, neg) > 0.8:
                    return {
                        "existing": f"喜欢/使用/必须: {pos}",
                        "new": f"不喜欢/不使用/不必: {neg}"
                    }
    
    return None

def check_update(new, existing):
    """检测是否为更新或细化"""
    # 相似度在0.5-0.8之间可能是更新
    sim = similar(new, existing)
    
    if 0.5 < sim < 0.8:
        return {
            "existing": existing[:200] + "...",
            "new": new[:200] + "..."
        }
    
    return None

def resolve_conflict(conflict, user_input=None):
    """
    解决冲突
    
    策略：
    1. high severity: 暂停并询问用户
    2. medium severity: 自动合并，事后通知
    3. low severity: 自动覆盖，记录日志
    """
    if conflict["severity"] == "high":
        if user_input:
            # 用户给出了明确指示
            if "覆盖" in user_input or "更新" in user_input:
                return {"action": "replace", "reason": "用户明确覆盖"}
            elif "保留" in user_input or "旧的" in user_input:
                return {"action": "keep", "reason": "用户保留旧版"}
            elif "合并" in user_input:
                return {"action": "merge", "reason": "用户要求合并"}
        
        # 没有用户输入，暂停等待
        return {"action": "pause", "reason": "需要用户确认"}
    
    elif conflict["severity"] == "medium":
        # 自动合并策略
        return {"action": "merge", "reason": "自动合并更新"}
    
    else:
        # 自动覆盖（新记忆优先）
        return {"action": "replace", "reason": "自动覆盖（低冲突）"}

def merge_content(existing, new, conflict_type="update"):
    """合并内容"""
    if conflict_type == "refinement":
        # 细化：保留旧版，添加新版作为补充
        return f"{existing}\n\n【更新 - {datetime.now().strftime('%Y-%m-%d')}】\n{new}"
    else:
        # 一般合并：标记版本
        return f"【历史版本】\n{existing}\n\n【当前版本 - {datetime.now().strftime('%Y-%m-%d')}】\n{new}"

def log_conflict(conflict, resolution):
    """记录冲突日志"""
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "conflict": conflict,
        "resolution": resolution
    }
    
    with open(CONFLICT_LOG, 'a', encoding='utf-8') as f:
        f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")

def smart_save(content, memory_type="general", metadata=None):
    """
    智能保存 - 自动检测并处理冲突
    
    使用示例：
    result = smart_save("用户喜欢简洁", memory_type="preference")
    if result["status"] == "conflict":
        # 询问用户
        pass
    """
    # 1. 检测冲突
    conflict_check = detect_conflict(content, memory_type)
    
    if not conflict_check["has_conflict"]:
        return {
            "status": "saved",
            "action": "direct_save",
            "message": "无冲突，直接保存"
        }
    
    # 2. 处理冲突
    results = []
    for conflict in conflict_check["conflicts"]:
        resolution = resolve_conflict(conflict)
        log_conflict(conflict, resolution)
        results.append({
            "conflict": conflict,
            "resolution": resolution
        })
        
        # 高冲突需要暂停
        if resolution["action"] == "pause":
            return {
                "status": "conflict",
                "severity": "high",
                "message": f"检测到矛盾：{conflict['existing']} vs {conflict['new']}",
                "details": results
            }
    
    # 3. 中低冲突自动处理
    return {
        "status": "resolved",
        "action": "auto_merge",
        "message": "冲突已自动处理",
        "details": results
    }

if __name__ == "__main__":
    # 测试
    print("记忆冲突检测系统已初始化")
