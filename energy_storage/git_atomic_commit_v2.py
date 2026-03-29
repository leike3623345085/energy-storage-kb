#!/usr/bin/env python3
"""
原子化 Git 提交系统 v2 - 优化版 (Atomic Git Commit System v2)
===============================================================

优化点:
1. 自动回滚机制 - 失败时自动回滚到上一状态
2. 提交消息模板 - 支持自定义模板和变量替换
3. 里程碑标记 - 自动/手动打 tag
4. 提交图谱 - 可视化提交历史
5. 变更集管理 - 批量原子提交
6. 预提交钩子 - 自动验证和格式化
"""

import subprocess
import json
import hashlib
import re
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any, Callable, Tuple
from dataclasses import dataclass, asdict, field
from enum import Enum
from collections import defaultdict
import logging
import tempfile
import shutil

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("GitAtomic-v2")


class TaskType(Enum):
    """任务类型 v2"""
    CRAWL = "crawl"
    CLEAN = "clean"
    ANALYZE = "analyze"
    GENERATE = "generate"
    SYNC = "sync"
    FIX = "fix"
    CONFIG = "config"
    DEPLOY = "deploy"
    TEST = "test"


class TaskStatus(Enum):
    """任务状态 v2"""
    SUCCESS = "✅"
    PARTIAL = "⚠️"
    FAILED = "❌"
    SKIPPED = "⏭️"
    ROLLED_BACK = "↩️"


@dataclass
class CommitTemplate:
    """提交消息模板"""
    name: str
    pattern: str
    variables: List[str] = field(default_factory=list)
    
    def render(self, **kwargs) -> str:
        """渲染模板"""
        result = self.pattern
        for var in self.variables:
            if var in kwargs:
                result = result.replace(f"{{{var}}}", str(kwargs[var]))
        return result


# 预定义模板
TEMPLATES = {
    "standard": CommitTemplate(
        name="standard",
        pattern="""[{type}] {name} {status}

{summary}

详细变更:
{details}

文件变更:
{files}

元数据:
{metadata}
""",
        variables=["type", "name", "status", "summary", "details", "files", "metadata"]
    ),
    "minimal": CommitTemplate(
        name="minimal",
        pattern="""[{type}] {name} {status}

{summary}
""",
        variables=["type", "name", "status", "summary"]
    ),
    "conventional": CommitTemplate(
        name="conventional",
        pattern="""{type}({scope}): {summary} {status}

{details}

{metadata}
""",
        variables=["type", "scope", "summary", "status", "details", "metadata"]
    )
}


@dataclass
class AtomicCommit:
    """原子提交定义 v2"""
    task_type: TaskType
    task_name: str
    status: TaskStatus
    summary: str
    details: List[str]
    files_changed: List[str]
    metadata: Dict[str, Any]
    parent_tasks: List[str] = field(default_factory=list)
    commit_hash: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    template: str = "standard"
    
    def generate_message(self, template_name: str = None) -> str:
        """生成提交信息"""
        template = TEMPLATES.get(template_name or self.template, TEMPLATES["standard"])
        
        # 格式化变量
        type_str = self.task_type.value.upper()
        status_str = self.status.value
        details_str = "\n".join(f"  - {d}" for d in self.details) if self.details else "  (无)"
        files_str = "\n".join(f"  - {f}" for f in self.files_changed[:10]) if self.files_changed else "  (无)"
        if len(self.files_changed) > 10:
            files_str += f"\n  ... 和 {len(self.files_changed) - 10} 个其他文件"
        metadata_str = "\n".join(f"  {k}: {v}" for k, v in self.metadata.items()) if self.metadata else "  (无)"
        
        return template.render(
            type=type_str,
            name=self.task_name,
            status=status_str,
            summary=self.summary,
            details=details_str,
            files=files_str,
            metadata=metadata_str
        )


class ChangeSet:
    """变更集 - 批量原子提交"""
    
    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description
        self.commits: List[AtomicCommit] = []
        self.start_time = datetime.now()
        self.end_time: Optional[datetime] = None
        self.rollback_point: Optional[str] = None
    
    def add(self, commit: AtomicCommit):
        """添加提交"""
        self.commits.append(commit)
    
    def complete(self):
        """完成变更集"""
        self.end_time = datetime.now()
    
    @property
    def duration(self) -> float:
        """变更集耗时"""
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return 0.0
    
    @property
    def is_successful(self) -> bool:
        """是否全部成功"""
        return all(c.status == TaskStatus.SUCCESS for c in self.commits)
    
    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "description": self.description,
            "commits": len(self.commits),
            "duration": self.duration,
            "successful": self.is_successful,
            "rollback_point": self.rollback_point
        }


class GitAtomicCommitV2:
    """原子化 Git 提交管理器 v2"""
    
    def __init__(self, repo_path: Optional[Path] = None, auto_commit: bool = True,
                 enable_rollback: bool = True, enable_hooks: bool = False):
        self.repo_path = repo_path or Path(__file__).parent
        self.auto_commit = auto_commit
        self.enable_rollback = enable_rollback
        self.enable_hooks = enable_hooks
        self.commit_history: List[AtomicCommit] = []
        self.change_sets: List[ChangeSet] = []
        self.current_branch = self._get_current_branch()
        self.enabled = self._is_git_repo()
        
        if not self.enabled:
            logger.warning("⚠️ 当前目录不是 Git 仓库，Git 提交功能将不可用")
        else:
            logger.info(f"✅ Git 原子提交系统 v2 初始化 | 分支: {self.current_branch}")
            if self.enable_rollback:
                logger.info("   🛡️ 自动回滚已启用")
    
    def _is_git_repo(self) -> bool:
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--git-dir"],
                cwd=self.repo_path,
                capture_output=True,
                text=True
            )
            return result.returncode == 0
        except:
            return False
    
    def _get_current_branch(self) -> str:
        try:
            result = subprocess.run(
                ["git", "branch", "--show-current"],
                cwd=self.repo_path,
                capture_output=True,
                text=True
            )
            return result.stdout.strip()
        except:
            return "unknown"
    
    def _run_git(self, args: List[str], check: bool = False) -> Tuple[int, str, str]:
        """运行 git 命令"""
        if not self.enabled:
            return (1, "", "Git 功能未启用")
        
        try:
            result = subprocess.run(
                ["git"] + args,
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=check
            )
            return (result.returncode, result.stdout, result.stderr)
        except Exception as e:
            return (1, "", str(e))
    
    def _get_current_commit(self) -> str:
        """获取当前 commit hash"""
        code, stdout, _ = self._run_git(["rev-parse", "HEAD"])
        return stdout.strip() if code == 0 else ""
    
    def stage_files(self, files: Optional[List[str]] = None, pattern: Optional[str] = None) -> bool:
        """暂存文件"""
        if files:
            for f in files:
                self._run_git(["add", f])
        elif pattern:
            self._run_git(["add", pattern])
        else:
            self._run_git(["add", "-A"])
        
        code, stdout, _ = self._run_git(["diff", "--cached", "--stat"])
        return code == 0 and bool(stdout.strip())
    
    def pre_commit_hook(self) -> Tuple[bool, str]:
        """预提交钩子 - 验证变更"""
        if not self.enable_hooks:
            return True, ""
        
        # 检查是否有变更
        code, stdout, _ = self._run_git(["diff", "--cached", "--stat"])
        if code != 0 or not stdout.strip():
            return False, "没有待提交的变更"
        
        # 检查大文件
        code, stdout, _ = self._run_git(["diff", "--cached", "--numstat"])
        for line in stdout.split('\n'):
            parts = line.split('\t')
            if len(parts) >= 3:
                try:
                    added = int(parts[0])
                    if added > 10000:  # 超过 10000 行
                        return False, f"检测到可能的大文件: {parts[2]}"
                except:
                    pass
        
        return True, ""
    
    def commit(self, atomic_commit: AtomicCommit, template: str = None) -> Optional[str]:
        """
        执行原子提交
        
        Returns:
            提交哈希，失败返回 None
        """
        if not self.enabled:
            logger.info(f"[模拟提交] {atomic_commit.task_name}")
            self.commit_history.append(atomic_commit)
            return "mock_commit_hash"
        
        # 记录回滚点
        rollback_point = self._get_current_commit() if self.enable_rollback else None
        
        # 预提交钩子
        if self.enable_hooks:
            ok, msg = self.pre_commit_hook()
            if not ok:
                logger.warning(f"预提交检查失败: {msg}")
                return None
        
        # 生成提交信息
        message = atomic_commit.generate_message(template)
        
        # 执行提交
        code, stdout, stderr = self._run_git(["commit", "-m", message])
        
        if code == 0:
            # 获取提交哈希
            _, hash_out, _ = self._run_git(["rev-parse", "HEAD"])
            commit_hash = hash_out.strip()[:8]
            atomic_commit.commit_hash = commit_hash
            
            logger.info(f"✅ 原子提交成功: {commit_hash} - {atomic_commit.task_name}")
            self.commit_history.append(atomic_commit)
            
            return commit_hash
        else:
            logger.error(f"❌ 提交失败: {stderr}")
            
            # 尝试回滚
            if self.enable_rollback and rollback_point:
                self._rollback_to(rollback_point, atomic_commit.task_name)
            
            return None
    
    def _rollback_to(self, commit_hash: str, context: str = ""):
        """回滚到指定提交"""
        logger.warning(f"🔄 回滚到 {commit_hash[:8]} (上下文: {context})")
        self._run_git(["reset", "--hard", commit_hash])
        logger.info(f"✅ 已回滚到 {commit_hash[:8]}")
    
    def rollback_last(self, keep_changes: bool = True) -> bool:
        """回滚最后一次提交"""
        if not self.enabled:
            logger.warning("Git 功能未启用，无法回滚")
            return False
        
        if keep_changes:
            code, _, _ = self._run_git(["reset", "--soft", "HEAD~1"])
        else:
            code, _, _ = self._run_git(["reset", "--hard", "HEAD~1"])
        
        if code == 0:
            logger.info(f"✅ 已回滚最后一次提交")
            if self.commit_history:
                self.commit_history[-1].status = TaskStatus.ROLLED_BACK
            return True
        return False
    
    def create_tag(self, tag_name: str, message: str = "", annotate: bool = True) -> bool:
        """创建标签（里程碑）"""
        if not self.enabled:
            return False
        
        if annotate:
            code, _, _ = self._run_git(["tag", "-a", tag_name, "-m", message or tag_name])
        else:
            code, _, _ = self._run_git(["tag", tag_name])
        
        if code == 0:
            logger.info(f"✅ 创建标签: {tag_name}")
            return True
        return False
    
    def create_milestone(self, name: str, description: str = "") -> bool:
        """创建里程碑标签"""
        timestamp = datetime.now().strftime("%Y%m%d")
        tag_name = f"milestone/{name}-{timestamp}"
        return self.create_tag(tag_name, description, annotate=True)
    
    def start_change_set(self, name: str, description: str = "") -> ChangeSet:
        """开始变更集"""
        cs = ChangeSet(name, description)
        cs.rollback_point = self._get_current_commit()
        self.change_sets.append(cs)
        logger.info(f"📦 开始变更集: {name}")
        return cs
    
    def end_change_set(self, cs: ChangeSet, auto_tag: bool = False) -> bool:
        """结束变更集"""
        cs.complete()
        
        if not cs.is_successful and self.enable_rollback and cs.rollback_point:
            logger.warning(f"变更集 {cs.name} 有失败任务，执行回滚")
            self._rollback_to(cs.rollback_point, f"变更集失败: {cs.name}")
            return False
        
        if auto_tag:
            self.create_milestone(cs.name, cs.description)
        
        logger.info(f"✅ 变更集完成: {cs.name} ({len(cs.commits)} 次提交)")
        return True
    
    def commit_task_result(self, task_type: TaskType, task_name: str, 
                          status: TaskStatus, summary: str,
                          details: List[str] = None,
                          files: List[str] = None,
                          metadata: Dict = None,
                          template: str = "standard",
                          change_set: ChangeSet = None) -> Optional[str]:
        """
        便捷的提交通用方法
        """
        atomic = AtomicCommit(
            task_type=task_type,
            task_name=task_name,
            status=status,
            summary=summary,
            details=details or [],
            files_changed=files or [],
            metadata=metadata or {},
            template=template
        )
        
        # 自动暂存文件
        if files:
            has_changes = self.stage_files(files)
        else:
            has_changes = self.stage_files()
        
        if not has_changes and self.enabled:
            logger.warning(f"⚠️ 没有文件变更，跳过提交: {task_name}")
            if change_set:
                change_set.add(atomic)
            return None
        
        commit_hash = self.commit(atomic, template)
        
        if change_set and commit_hash:
            change_set.add(atomic)
        
        return commit_hash
    
    def generate_commit_graph(self) -> str:
        """生成提交图谱（Mermaid 格式）"""
        lines = ["```mermaid", "gitGraph"]
        
        for commit in self.commit_history:
            type_str = commit.task_type.value
            status_str = "commit" if commit.status == TaskStatus.SUCCESS else "commit id: \"❌\""
            lines.append(f"    {status_str} \"{commit.task_name[:20]}\"")
        
        lines.append("```")
        return "\n".join(lines)
    
    def get_commit_stats(self) -> Dict:
        """获取提交统计"""
        stats = {
            "total_commits": len(self.commit_history),
            "by_type": defaultdict(int),
            "by_status": defaultdict(int),
            "by_date": defaultdict(int),
            "timeline": []
        }
        
        for commit in self.commit_history:
            t = commit.task_type.value
            stats["by_type"][t] += 1
            
            s = commit.status.value
            stats["by_status"][s] += 1
            
            d = commit.timestamp.strftime("%Y-%m-%d")
            stats["by_date"][d] += 1
            
            stats["timeline"].append({
                "time": commit.timestamp.isoformat(),
                "task": commit.task_name,
                "type": t,
                "status": s
            })
        
        return dict(stats)
    
    def save_report(self, output_path: Optional[Path] = None) -> Path:
        """保存提交报告"""
        if output_path is None:
            output_path = self.repo_path / "data" / "git_atomic_logs"
        
        output_path.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = output_path / f"git_atomic_report_v2_{timestamp}.json"
        
        # 序列化提交历史
        serializable_commits = []
        for c in self.commit_history:
            commit_dict = {
                "task_type": c.task_type.value,
                "task_name": c.task_name,
                "status": c.status.value,
                "summary": c.summary,
                "commit_hash": c.commit_hash,
                "timestamp": c.timestamp.isoformat(),
                "template": c.template
            }
            serializable_commits.append(commit_dict)
        
        report = {
            "generated_at": datetime.now().isoformat(),
            "branch": self.current_branch,
            "total_commits": len(self.commit_history),
            "total_change_sets": len(self.change_sets),
            "commits": serializable_commits,
            "change_sets": [cs.to_dict() for cs in self.change_sets],
            "stats": self.get_commit_stats()
        }
        
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        logger.info(f"💾 提交报告已保存: {report_file}")
        return report_file


class HarnessGitIntegrationV2:
    """HARNESS 框架的 Git 集成 v2"""
    
    def __init__(self, repo_path: Optional[Path] = None):
        self.git = GitAtomicCommitV2(repo_path, enable_rollback=True)
        self.current_change_set: Optional[ChangeSet] = None
    
    def start_pipeline(self, name: str) -> ChangeSet:
        """开始流水线"""
        self.current_change_set = self.git.start_change_set(name)
        return self.current_change_set
    
    def end_pipeline(self, auto_tag: bool = True) -> bool:
        """结束流水线"""
        if self.current_change_set:
            result = self.git.end_change_set(self.current_change_set, auto_tag)
            self.current_change_set = None
            return result
        return False
    
    def on_crawl_complete(self, source_name: str, items_count: int, 
                         output_file: Path, duration: float) -> Optional[str]:
        """爬虫完成后自动提交"""
        return self.git.commit_task_result(
            task_type=TaskType.CRAWL,
            task_name=f"{source_name} 数据爬取",
            status=TaskStatus.SUCCESS if items_count > 0 else TaskStatus.PARTIAL,
            summary=f"成功获取 {items_count} 条数据",
            details=[
                f"数据源: {source_name}",
                f"数据量: {items_count} 条",
                f"耗时: {duration:.1f}s"
            ],
            files=[str(output_file)] if output_file else None,
            metadata={"source": source_name, "items": items_count, "duration": duration},
            change_set=self.current_change_set
        )
    
    def on_report_generated(self, report_file: Path, sections: List[str],
                           confidence_score: int) -> Optional[str]:
        """报告生成后自动提交"""
        return self.git.commit_task_result(
            task_type=TaskType.GENERATE,
            task_name="日报生成",
            status=TaskStatus.SUCCESS if confidence_score >= 80 else TaskStatus.PARTIAL,
            summary=f"生成包含 {len(sections)} 个章节的日报",
            details=[f"章节: {', '.join(sections)}"],
            files=[str(report_file)],
            metadata={"sections": len(sections), "confidence": confidence_score},
            change_set=self.current_change_set
        )


# ============== 使用示例 ==============

def demo_v2():
    """演示 v2 版本"""
    print("\n" + "=" * 70)
    print("原子化 Git 提交系统 v2 - 优化版")
    print("=" * 70)
    
    git = GitAtomicCommitV2(enable_rollback=True)
    
    if not git.enabled:
        print("\n⚠️ 当前不是 Git 仓库，以下为模拟演示")
    
    # 开始变更集
    cs = git.start_change_set("日报生成流水线", "生成 2026-03-29 储能日报")
    
    # 提交 1: 爬虫
    commit1 = git.commit_task_result(
        task_type=TaskType.CRAWL,
        task_name="北极星储能网爬虫",
        status=TaskStatus.SUCCESS,
        summary="成功获取 94 条新闻",
        details=["新增数据 94 条", "去重后有效 94 条", "耗时: 12.5s"],
        files=["data/crawler/bjx_20260329.json"],
        metadata={"source": "北极星", "items": 94, "duration": 12.5},
        change_set=cs
    )
    
    # 提交 2: 数据清洗
    commit2 = git.commit_task_result(
        task_type=TaskType.CLEAN,
        task_name="数据清洗合并",
        status=TaskStatus.SUCCESS,
        summary="合并3个数据源，去重后 106 条",
        details=["原始数据: 120 条", "去重后: 106 条"],
        files=["data/cleaned/news_merged_20260329.json"],
        metadata={"sources": 3, "before": 120, "after": 106},
        change_set=cs
    )
    
    # 结束变更集
    git.end_change_set(cs, auto_tag=True)
    
    # 查看统计
    stats = git.get_commit_stats()
    print("\n提交统计:")
    print(f"  总提交数: {stats['total_commits']}")
    print(f"  按类型: {dict(stats['by_type'])}")
    print(f"  按状态: {dict(stats['by_status'])}")
    
    # 提交图谱
    print("\n提交图谱:")
    print(git.generate_commit_graph())
    
    # 保存报告
    report_file = git.save_report()
    print(f"\n💾 报告已保存: {report_file}")


if __name__ == "__main__":
    demo_v2()
