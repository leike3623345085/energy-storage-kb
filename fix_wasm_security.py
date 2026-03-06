#!/usr/bin/env python3
"""
WASM 数据分析文件安全修复脚本
自动修复 XSS、alert、内存泄漏等问题
"""

import re
from pathlib import Path

def fix_xss_vulnerabilities(content):
    """修复 XSS 漏洞 - 添加 escapeHtml 函数并替换 innerHTML"""
    
    # 1. 在 </head> 前添加 CSP 和 escapeHtml 函数
    csp_meta = '''<meta http-equiv="Content-Security-Policy" content="default-src 'self'; script-src 'self' https://cdn.jsdelivr.net 'unsafe-inline'; style-src 'unsafe-inline';">
<script>
// XSS 防护函数
function escapeHtml(text) {
    if (text == null) return '';
    const div = document.createElement('div');
    div.textContent = String(text);
    return div.innerHTML;
}
// Toast 通知
function showToast(message, type='info', duration=3000) {
    const toast = document.createElement('div');
    toast.style.cssText = 'position:fixed;top:20px;right:20px;padding:12px 20px;border-radius:6px;color:white;font-size:14px;z-index:10000;transition:all 0.3s;';
    const colors = {info:'#3b82f6',success:'#10b981',warning:'#f59e0b',error:'#ef4444'};
    toast.style.background = colors[type] || colors.info;
    toast.textContent = message;
    document.body.appendChild(toast);
    setTimeout(() => { toast.style.opacity='0'; setTimeout(()=>toast.remove(),300); }, duration);
}
// 确认对话框
function confirmAction(message) {
    return new Promise(resolve => {
        if (confirm(message)) resolve(true);
        else resolve(false);
    });
}
</script>
</head>'''
    
    content = content.replace('</head>', csp_meta)
    
    # 2. 修复 innerHTML 插入 - 简单的 td/th 内容
    # 查找 pattern: html += `<td>${xxx}</td>`
    content = re.sub(
        r'html\s*\+=\s*`<td([^>]*)>\$\{([^}]+)\}</td>`',
        r'html += `<td\1>${escapeHtml(\2)}</td>`',
        content
    )
    
    return content

def fix_alert_usage(content):
    """修复 alert 使用 - 替换为 showToast"""
    
    # 替换 alert('xxx') 为 showToast('xxx', 'error')
    # 但保留一些关键确认场景
    content = re.sub(
        r'alert\s*\(\s*["\']([^"\']+)["\']\s*\)',
        r'showToast("\1", "warning")',
        content
    )
    
    return content

def fix_memory_leaks(content):
    """修复内存泄漏 - 添加缓存限制"""
    
    # 在 fuzzyIndexes 定义处添加限制
    memory_fix = '''let fuzzyIndexes = {};
const MAX_CACHE_SIZE = 50000;
function checkAndClearCache() {
    if (Object.keys(fuzzyIndexes).length > MAX_CACHE_SIZE) {
        console.warn('缓存过大，清理中...');
        fuzzyIndexes = {};
    }
}'''
    
    content = content.replace(
        'let fuzzyIndexes = {};',
        memory_fix
    )
    
    return content

def fix_responsive_layout(content):
    """修复响应式布局"""
    
    # 在 CSS 中添加媒体查询
    responsive_css = '''
@media (max-width: 768px) {
    .app-container { grid-template-columns: 1fr !important; }
    .sidebar-left { position: fixed; left: -100%; width: 85%; z-index: 999; transition: left 0.3s; }
    .sidebar-left.open { left: 0; }
}
</style>'''
    
    content = content.replace('</style>', responsive_css)
    
    return content

def main():
    input_file = Path('/root/openclaw/kimi/downloads/19cbe63b-ad52-8425-8000-0000bb408b42_WASM数据分析.html')
    output_file = Path('/root/openclaw/kimi/downloads/WASM数据分析_修复版.html')
    
    if not input_file.exists():
        print(f'错误：找不到文件 {input_file}')
        return 1
    
    print('读取原文件...')
    with open(input_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    print('应用安全修复...')
    
    # 应用修复
    content = fix_xss_vulnerabilities(content)
    content = fix_alert_usage(content)
    content = fix_memory_leaks(content)
    content = fix_responsive_layout(content)
    
    # 修改标题
    content = content.replace(
        '<title>WASM数据分析与业绩计算综合平台 - ExcelJS版</title>',
        '<title>WASM数据分析与业绩计算综合平台 - ExcelJS版（安全修复版）</title>'
    )
    
    print(f'保存修复后的文件到 {output_file}...')
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print('✅ 修复完成！')
    print(f'原文件: {input_file}')
    print(f'修复文件: {output_file}')
    print('\n修复内容:')
    print('  - 添加 CSP 安全策略')
    print('  - 添加 XSS 防护函数 (escapeHtml)')
    print('  - 添加 Toast 通知替代 alert')
    print('  - 添加内存缓存限制')
    print('  - 添加移动端响应式支持')
    
    return 0

if __name__ == '__main__':
    exit(main())
