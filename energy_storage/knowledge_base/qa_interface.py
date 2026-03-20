#!/usr/bin/env python3
"""
储能知识库智能问答接口
支持自然语言提问，从向量知识库检索答案
"""

import json
import sys
from pathlib import Path
from typing import List, Dict

# 添加父目录到路径
sys.path.insert(0, str(Path(__file__).parent))
from vector_kb import VectorKnowledgeBase

class EnergyStorageQA:
    """储能行业智能问答系统"""
    
    def __init__(self):
        self.kb = VectorKnowledgeBase()
    
    def ask(self, question: str) -> str:
        """
        回答用户问题
        
        流程：
        1. 理解问题意图
        2. 检索相关内容
        3. 生成答案
        """
        # 查询知识库
        result = self.kb.query(question, context_chunks=5)
        
        if result['confidence'] < 0.1:
            return self._format_no_answer(question)
        
        # 构建答案
        answer = self._generate_answer(question, result)
        return answer
    
    def _generate_answer(self, question: str, result: Dict) -> str:
        """基于检索结果生成答案"""
        sources = result['sources']
        context = result['context']
        confidence = result['confidence']
        
        # 提取关键信息
        answer_parts = []
        
        # 开头
        answer_parts.append(f"📋 **关于「{question}」的信息**\n")
        
        # 根据问题类型整理内容
        if "政策" in question or "通知" in question or "意见" in question:
            answer_parts.append(self._extract_policies(context))
        elif "公司" in question or "企业" in question or "签署" in question or "合作" in question:
            answer_parts.append(self._extract_companies(context))
        elif "项目" in question or "投产" in question or "开工" in question or "建设" in question:
            answer_parts.append(self._extract_projects(context))
        elif "技术" in question or "突破" in question or "研发" in question or "专利" in question:
            answer_parts.append(self._extract_tech(context))
        elif "价格" in question or "涨价" in question or "降价" in question or "成本" in question:
            answer_parts.append(self._extract_prices(context))
        else:
            answer_parts.append(self._extract_general(context))
        
        # 信息来源
        answer_parts.append("\n📚 **信息来源**:")
        unique_sources = {}
        for s in sources:
            key = f"{s['title']}_{s['date']}"
            if key not in unique_sources:
                unique_sources[key] = s
        
        for s in unique_sources.values():
            answer_parts.append(f"- {s['title']} ({s['date']})")
        
        # 置信度提示
        if confidence < 0.3:
            answer_parts.append("\n⚠️ **提示**: 相关内容较少，答案可能不够完整")
        
        return "\n".join(answer_parts)
    
    def _extract_policies(self, context: str) -> str:
        """提取政策相关信息"""
        lines = []
        lines.append("📜 **政策动态**: \n")
        
        # 简单提取包含政策关键词的段落
        paragraphs = context.split('\n\n')
        for p in paragraphs:
            if any(kw in p for kw in ['政策', '通知', '意见', '发布', '印发', '国家', '工信部', '能源局']):
                # 清理并格式化
                p = p.strip()
                if len(p) > 20:
                    lines.append(f"• {p[:200]}{'...' if len(p) > 200 else ''}")
        
        return '\n'.join(lines) if len(lines) > 1 else "暂无具体政策信息"
    
    def _extract_companies(self, context: str) -> str:
        """提取企业相关信息"""
        lines = []
        lines.append("🏢 **企业动态**: \n")
        
        paragraphs = context.split('\n\n')
        for p in paragraphs:
            if any(kw in p for kw in ['宁德时代', '比亚迪', '亿纬', '阳光电源', '特斯拉', '签署', '合作', '订单']):
                p = p.strip()
                if len(p) > 20:
                    lines.append(f"• {p[:200]}{'...' if len(p) > 200 else ''}")
        
        return '\n'.join(lines) if len(lines) > 1 else "暂无具体企业信息"
    
    def _extract_projects(self, context: str) -> str:
        """提取项目相关信息"""
        lines = []
        lines.append("🏗️ **项目进展**: \n")
        
        paragraphs = context.split('\n\n')
        for p in paragraphs:
            if any(kw in p for kw in ['项目', '投产', '开工', '建设', '基地', '电站', 'GWh', 'MW']):
                p = p.strip()
                if len(p) > 20:
                    lines.append(f"• {p[:200]}{'...' if len(p) > 200 else ''}")
        
        return '\n'.join(lines) if len(lines) > 1 else "暂无具体项目信息"
    
    def _extract_tech(self, context: str) -> str:
        """提取技术相关信息"""
        lines = []
        lines.append("🔬 **技术进展**: \n")
        
        paragraphs = context.split('\n\n')
        for p in paragraphs:
            if any(kw in p for kw in ['技术', '研发', '突破', '专利', '创新', '实验室', '量产']):
                p = p.strip()
                if len(p) > 20:
                    lines.append(f"• {p[:200]}{'...' if len(p) > 200 else ''}")
        
        return '\n'.join(lines) if len(lines) > 1 else "暂无具体技术信息"
    
    def _extract_prices(self, context: str) -> str:
        """提取价格相关信息"""
        lines = []
        lines.append("💰 **价格动态**: \n")
        
        paragraphs = context.split('\n\n')
        for p in paragraphs:
            if any(kw in p for kw in ['价格', '元', '万元', '亿元', '$', '涨价', '降价']):
                p = p.strip()
                if len(p) > 20:
                    lines.append(f"• {p[:200]}{'...' if len(p) > 200 else ''}")
        
        return '\n'.join(lines) if len(lines) > 1 else "暂无具体价格信息"
    
    def _extract_general(self, context: str) -> str:
        """通用信息提取"""
        lines = []
        lines.append("📰 **相关内容**: \n")
        
        paragraphs = context.split('\n\n')
        count = 0
        for p in paragraphs:
            p = p.strip()
            if len(p) > 30 and count < 5:
                lines.append(f"• {p[:200]}{'...' if len(p) > 200 else ''}")
                count += 1
        
        return '\n'.join(lines) if len(lines) > 1 else context[:500]
    
    def _format_no_answer(self, question: str) -> str:
        """格式化无答案响应"""
        return f"""📭 **未找到相关信息**

关于「{question}」，当前知识库中没有匹配的内容。

可能原因：
- 相关报告尚未生成或索引
- 问题表述与文档内容差异较大
- 该话题最近没有报道

建议：
1. 尝试用其他关键词提问
2. 检查报告生成状态
3. 稍后再试（新报告每日18:00更新）
"""

def main():
    """CLI入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description="储能知识库问答")
    parser.add_argument("question", nargs="?", help="问题")
    parser.add_argument("--interactive", "-i", action="store_true",
                        help="交互模式")
    
    args = parser.parse_args()
    
    qa = EnergyStorageQA()
    
    if args.interactive or not args.question:
        print("\n🤖 储能行业智能问答")
        print("输入问题，或输入 'quit' 退出\n")
        
        while True:
            try:
                question = input("❓ ").strip()
                if question.lower() in ['quit', 'exit', 'q', '退出']:
                    print("再见！")
                    break
                if not question:
                    continue
                
                print("\n" + qa.ask(question))
                print("\n" + "=" * 60 + "\n")
                
            except KeyboardInterrupt:
                print("\n再见！")
                break
    else:
        print(qa.ask(args.question))
    
    return 0

if __name__ == "__main__":
    exit(main())
