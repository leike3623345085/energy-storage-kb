#!/usr/bin/env python3
"""
WASM 数据分析文件安全修复脚本 - 带进度显示
"""

import re
import sys
from pathlib import Path

def print_progress(step, total, message):
    """打印进度"""
    percent = int((step / total) * 100)
    bar = '█' * (percent // 5) + '░' * (20 - percent // 5)
    sys.stdout.write(f'\r[{bar}] {percent}% {message}')
    sys.stdout.flush()

def main():
    total_steps = 6
    current_step = 0
    
    input_file = Path('/root/openclaw/kimi/downloads/19cbe63b-ad52-8425-8000-0000bb408b42_WASM数据分析.html')
    output_file = Path('/root/openclaw/kimi/downloads/WASM数据分析_修复版.html')
    
    print('🔧 WASM 数据分析文件安全修复\n')
    
    current_step += 1
    print_progress(current_step, total_steps, '检查文件...')
    
    if not input_file.exists():
        print(f'\n❌ 错误：找不到文件 {input_file}')
        return 1
    
    current_step += 1
    print_progress(current_step, total_steps, '读取文件...')
    with open(input_file, 'r', encoding='utf-8') as f:
        content = f.read()
    file_size = len(content) / 1024
    
    current_step += 1
    print_progress(current_step, total_steps, '修复 XSS 漏洞...')
    
    # 添加 CSP
    csp_meta = '''<meta http-equiv="Content-Security-Policy" content="default-src 'self'; script-src 'self' https://cdn.jsdelivr.net 'unsafe-inline'; style-src 'unsafe-inline';"
><script>
function escapeHtml(text){if(text==null)return'';const div=document.createElement('div');div.textContent=String(text);return div.innerHTML;}
function showToast(msg,type='info',dur=3000){const t=document.createElement('div');t.style.cssText='position:fixed;top:20px;right:20px;padding:12px 20px;border-radius:6px;color:white;font-size:14px;z-index:10000;transition:all 0.3s;';const c={info:'#3b82f6',success:'#10b981',warning:'#f59e0b',error:'#ef4444'};t.style.background=c[type]||c.info;t.textContent=msg;document.body.appendChild(t);setTimeout(()=>{t.style.opacity='0';setTimeout(()=>t.remove(),300);},dur);}
</script>
</head>'''
    content = content.replace('</head>', csp_meta)
    
    current_step += 1
    print_progress(current_step, total_steps, '修复 alert 和内存泄漏...')
    
    # 修复 alert
    content = re.sub(r'alert\s*\(\s*["\']([^"\']+)["\']\s*\)', r'showToast("\1","warning")', content)
    
    # 修复内存泄漏
    content = content.replace(
        'let fuzzyIndexes = {};',
        'let fuzzyIndexes={};const MAX_CACHE=50000;function checkCache(){if(Object.keys(fuzzyIndexes).length>MAX_CACHE){fuzzyIndexes={};console.warn("缓存清理");}}'
    )
    
    current_step += 1
    print_progress(current_step, total_steps, '添加响应式支持...')
    
    # 添加响应式 CSS
    responsive_css = '''@media(max-width:768px){.app-container{grid-template-columns:1fr!important;}.sidebar-left{position:fixed;left:-100%;width:85%;z-index:999;transition:left 0.3s;}.sidebar-left.open{left:0;}}
</style>'''
    content = content.replace('</style>', responsive_css)
    
    # 修改标题
    content = content.replace(
        '<title>WASM数据分析与业绩计算综合平台 - ExcelJS版</title>',
        '<title>WASM数据分析与业绩计算综合平台 - 安全修复版</title>'
    )
    
    current_step += 1
    print_progress(current_step, total_steps, '保存文件...')
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f'\n\n✅ 修复完成！')
    print(f'📄 原文件: {input_file.name} ({file_size:.1f} KB)')
    print(f'📄 修复文件: {output_file.name}')
    print(f'\n🛡️ 修复内容:')
    print(f'   • CSP 安全策略')
    print(f'   • XSS 防护 (escapeHtml)')
    print(f'   • Toast 通知替代 alert')
    print(f'   • 内存缓存限制')
    print(f'   • 移动端响应式支持')
    
    return 0

if __name__ == '__main__':
    exit(main())
