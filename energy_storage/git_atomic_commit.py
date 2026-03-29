#!/usr/bin/env python3
"""
原子化 Git 提交系统 (Atomic Git Commit System)
==============================================
基于 GSD 和 Superpowers 方法论的自动 Git 工作流

核心特性:
- 任务级原子提交（每个子任务完成后自动提交）
- 结构化提交信息（包含任务类型、结果摘要）
- 自动标记和版本管理
- 失败回滚支持
- 与 HARNESS 反馈循环集成

提交格式:
    [任务类型] 任务名称 - 结果状态
    
    - 执行详情
    - 数据摘要
    - 关联任务
"""

import subprocess
import json
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, asdict
from enum import Enum
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("GitAtomic")


class TaskType(Enum):
    """任务类型"""
    CRAWL = "crawl"           # 数据爬取
    CLEAN = "clean"           # 数据清洗
    ANALYZE = "analyze"       # 数据分析
    GENERATE = "generate"     # 报告生成
    SYNC = "sync"             # 数据同步
    FIX = "fix"               # 问题修复
    CONFIG = "config"         # 配置变更


class TaskStatus(Enum):
    """任务状态"""
    SUCCESS = "✅"
    PARTIAL = "⚠️"
    FAILED = "❌"
    SKIPPED = "⏭️"


@dataclass
class AtomicCommit:
    """原子提交定义"""
    task_type: TaskType
    task_name: str
    status: TaskStatus
    summary: str
    details: List[str]
    files_changed: List[str]
    metadata: Dict[str, Any]
    parent_tasks: List[str] = None
    
    def __post_init__(self):
        if self.parent_tasks is None:
            self.parent_tasks = []
    
    def generate_message(self) -> str:
        """生成提交信息"""
        lines = [
            f"[{self.task_type.value.upper()}] {self.task_name} {self.status.value}",
            "",
            self.summary,
            "",
            "详细变更:",
        ]
        
        for detail in self.details:
            lines.append(f"  - {detail}")
        
        if self.files_changed:
            lines.extend(["", "文件变更:"])
            for f in self.files_changed[:10]:  # 最多显示10个
                lines.append(f"  - {f}")
            if len(self.files_changed) > 10:
                lines.append(f"  ... 和 {len(self.files_changed) - 10} 个其他文件")
        
        if self.metadata:
            lines.extend(["", "元数据:"])
            for k, v in self.metadata.items():
                lines.append(f"  {k}: {v}")
        
        if self.parent_tasks:
            lines.extend(["", "依赖任务:", f"  {', '.join(self.parent_tasks)}"])
        
        return "\n".join(lines)
    
    def generate_branch_name(self) -> str:
        """生成分支名称（用于独立工作流）"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        task_slug = self.task_name.lower().replace(" ", "_")[:30]
        return f"{self.task_type.value}/{task_slug}_{timestamp}"


class GitAtomicCommit:
    """原子化 Git 提交管理器"""
    
    def __init__(self, repo_path: Optional[Path] = None, auto_commit: bool = True):
        self.repo_path = repo_path or Path(__file__).parent
        self.auto_commit = auto_commit
        self.commit_history: List[AtomicCommit] = []
        self.current_branch = self._get_current_branch()
        
        # 检查是否在 git 仓库中
        if not self._is_git_repo():
            logger.warning("⚠️ 当前目录不是 Git 仓库，Git 提交功能将不可用")
            self.enabled = False
        else:
            self.enabled = True
            logger.info(f"✅ Git 原子提交系统初始化 | 分支: {self.current_branch}")
    
    def _is_git_repo(self) -> bool:
        """检查是否在 git 仓库中"""
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
        """获取当前分支"""
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
    
    def _run_git(self, args: List[str]) -> tuple:
        """运行 git 命令"""
        if not self.enabled:
            return (1, "", "Git 功能未启用")
        
        try:
            result = subprocess.run(
                ["git"] + args,
                cwd=self.repo_path,
                capture_output=True,
                text=True
            )
            return (result.returncode, result.stdout, result.stderr)
        except Exception as e:
            return (1, "", str(e))
    
    def stage_files(self, files: Optional[List[str]] = None, pattern: Optional[str] = None) -> bool:
        """
        暂存文件
        
        Args:
            files: 具体文件列表
            pattern: 匹配模式（如 "*.py"）
        """
        if files:
            for f in files:
                self._run_git(["add", f])
        elif pattern:
            self._run_git(["add", pattern])
        else:
            # 暂存所有变更
            self._run_git(["add", "-A"])
        
        # 检查是否有待提交的变更
        code, stdout, _ = self._run_git(["diff", "--cached", "--stat"])
        return code == 0 and bool(stdout.strip())
    
    def commit(self, atomic_commit: AtomicCommit) -> Optional[str]:
        """
        执行原子提交
        
        Returns:
            提交哈希，失败返回 None
        """
        if not self.enabled:
            logger.info(f"[模拟提交] {atomic_commit.task_name}")
            self.commit_history.append(atomic_commit)
            return "mock_commit_hash"
        
        # 生成提交信息
        message = atomic_commit.generate_message()
        
        # 执行提交
        code, stdout, stderr = self._run_git(["commit", "-m", message])
        
        if code == 0:
            # 获取提交哈希
            _, hash_out, _ = self._run_git(["rev-parse", "HEAD"])
            commit_hash = hash_out.strip()[:8]
            
            logger.info(f"✅ 原子提交成功: {commit_hash} - {atomic_commit.task_name}")
            self.commit_history.append(atomic_commit)
            
            return commit_hash
        else:
            logger.error(f"❌ 提交失败: {stderr}")
            return None
    
    def commit_task_result(self, task_type: TaskType, task_name: str, 
                          status: TaskStatus, summary: str,
                          details: List[str] = None,
                          files: List[str] = None,
                          metadata: Dict = None) -> Optional[str]:
        """
        便捷的提交通用方法
        
        使用示例:
            git.commit_task_result(
                task_type=TaskType.CRAWL,
                task_name="北极星储能网爬虫",
                status=TaskStatus.SUCCESS,
                summary="成功获取 94 条新闻",
                details=["新增数据 94 条", "去重后有效 94 条"],
                files=["data/crawler/news_20260329.json"],
                metadata={"source": "北极星", "duration": 12.5}
            )
        """
        atomic = AtomicCommit(
            task_type=task_type,
            task_name=task_name,
            status=status,
            summary=summary,
            details=details or [],
            files_changed=files or [],
            metadata=metadata or {}
        )
        
        # 自动暂存文件
        if files:
            self.stage_files(files)
        else:
            self.stage_files()
        
        return self.commit(atomic)
    
    def rollback_last(self) -> bool:
        """回滚最后一次提交（保留变更）"""
        if not self.enabled:
            logger.warning("Git 功能未启用，无法回滚")
            return False
        
        code, _, _ = self._run_git(["reset", "--soft", "HEAD~1"])
        if code == 0:
            logger.info("✅ 已回滚最后一次提交（变更保留在工作区）")
            if self.commit_history:
                self.commit_history.pop()
            return True
        return False
    
    def create_tag(self, tag_name: str, message: str = "") -> bool:
        """创建标签（用于里程碑）"""
        if not self.enabled:
            return False
        
        code, _, _ = self._run_git(["tag", "-a", tag_name, "-m", message or tag_name])
        if code == 0:
            logger.info(f"✅ 创建标签: {tag_name}")
            return True
        return False
    
    def get_commit_stats(self) -> Dict:
        """获取提交统计"""
        stats = {
            "total_commits": len(self.commit_history),
            "by_type": {},
            "by_status": {},
            "timeline": []
        }
        
        for commit in self.commit_history:
            # 按类型统计
            t = commit.task_type.value
            stats["by_type"][t] = stats["by_type"].get(t, 0) + 1
            
            # 按状态统计
            s = commit.status.value
            stats["by_status"][s] = stats["by_status"].get(s, 0) + 1
            
            # 时间线
            stats["timeline"].append({
                "task": commit.task_name,
                "type": t,
                "status": s
            })
        
        return stats
    
    def save_report(self, output_path: Optional[Path] = None):
        """保存提交报告"""
        if output_path is None:
            output_path = self.repo_path / "data" / "git_atomic_logs"
        
        output_path.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = output_path / f"git_atomic_report_{timestamp}.json"
        
        # 转换 commits 为可序列化的格式
        serializable_commits = []
        for c in self.commit_history:
            commit_dict = {
                "task_type": c.task_type.value if hasattr(c.task_type, 'value') else str(c.task_type),
                "task_name": c.task_name,
                "status": c.status.value if hasattr(c.status, 'value') else str(c.status),
                "summary": c.summary,
                "details": c.details,
                "files_changed": c.files_changed,
                "metadata": c.metadata,
                "parent_tasks": c.parent_tasks
            }
            serializable_commits.append(commit_dict)
        
        # 转换 stats
        stats = self.get_commit_stats()
        serializable_stats = {
            "total_commits": stats["total_commits"],
            "by_type": {k: v for k, v in stats["by_type"].items()},
            "by_status": {k: v for k, v in stats["by_status"].items()},
            "timeline": stats["timeline"]
        }
        
        report = {
            "generated_at": datetime.now().isoformat(),
            "branch": self.current_branch,
            "total_commits": len(self.commit_history),
            "commits": serializable_commits,
            "stats": serializable_stats
        }
        
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        logger.info(f"💾 提交报告已保存: {report_file}")
        return report_file


# ============== 与 HARNESS 集成 ==============

class HarnessGitIntegration:
    """HARNESS 框架的 Git 集成"""
    
    def __init__(self, repo_path: Optional[Path] = None):
        self.git = GitAtomicCommit(repo_path)
    
    def on_crawl_complete(self, source_name: str, items_count: int, 
                         output_file: Path, duration: float):
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
            metadata={"source": source_name, "items": items_count, "duration": duration}
        )
    
    def on_report_generated(self, report_file: Path, sections: List[str],
                           confidence_score: int):
        """报告生成后自动提交"""
        return self.git.commit_task_result(
            task_type=TaskType.GENERATE,
            task_name="日报生成",
            status=TaskStatus.SUCCESS if confidence_score >= 80 else TaskStatus.PARTIAL,
            summary=f"生成包含 {len(sections)} 个章节的日报",
            details=[f"章节: {', '.join(sections)}"],
            files=[str(report_file)],
            metadata={"sections": len(sections), "confidence": confidence_score}
        )
    
    def on_sync_complete(self, platform: str, synced_count: int, 
                        status: str = "success"):
        """同步完成后自动提交"""
        status_map = {
            "success": TaskStatus.SUCCESS,
            "partial": TaskStatus.PARTIAL,
            "failed": TaskStatus.FAILED
        }
        
        return self.git.commit_task_result(
            task_type=TaskType.SYNC,
            task_name=f"{platform} 数据同步",
            status=status_map.get(status, TaskStatus.PARTIAL),
            summary=f"同步 {synced_count} 条记录到 {platform}",
            details=[f"平台: {platform}", f"同步量: {synced_count}"],
            metadata={"platform": platform, "count": synced_count}
        )


# ============== 使用示例 ==============

def example_usage():
    """使用示例"""
    
    # 初始化
    git = GitAtomicCommit()
    
    if not git.enabled:
        print("⚠️ 当前不是 Git 仓库，以下为模拟演示")
    
    # 示例 1: 爬虫任务提交
    commit1 = git.commit_task_result(
        task_type=TaskType.CRAWL,
        task_name="北极星储能网爬虫",
        status=TaskStatus.SUCCESS,
        summary="成功获取 94 条新闻",
        details=[
            "新增数据 94 条",
            "去重后有效 94 条",
            "成功率: 100%"
        ],
        files=["data/crawler/news_20260329.json"],
        metadata={
            "source": "北极星储能网",
            "duration": 12.5,
            "worker": "crawler_parallel"
        }
    )
    
    # 示例 2: 报告生成提交
    commit2 = git.commit_task_result(
        task_type=TaskType.GENERATE,
        task_name="储能日报生成",
        status=TaskStatus.SUCCESS,
        summary="生成 2026-03-29 日报",
        details=[
            "章节: 市场动态, 技术进展, 政策动态, 行情数据, 今日热点",
            "置信度评分: 90/100",
            "数据量: 196 条"
        ],
        files=["data/reports/report_20260329.md"],
        metadata={
            "date": "2026-03-29",
            "confidence": 90,
            "data_sources": 4
        }
    )
    
    # 查看统计
    stats = git.get_commit_stats()
    print("\n" + "=" * 60)
    print("提交统计")
    print("=" * 60)
    print(f"总提交数: {stats['total_commits']}")
    print(f"按类型: {stats['by_type']}")
    print(f"按状态: {stats['by_status']}")
    
    # 保存报告
    git.save_report()


if __name__ == "__main__":
    print("原子化 Git 提交系统 - 示例运行")
    print("=" * 60)
    example_usage()
