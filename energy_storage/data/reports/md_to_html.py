#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Markdown to HTML Converter with proper Chinese font support
"""

import re
import os

def md_to_html(md_content, title="文档"):
    """Convert Markdown to HTML with full UTF-8 support"""
    
    html_content = md_content
    
    # Escape HTML special chars first
    html_content = html_content.replace('&', '&amp;')
    html_content = html_content.replace('<', '&lt;')
    html_content = html_content.replace('>', '&gt;')
    
    # Headers
    html_content = re.sub(r'^### (.+)$', r'<h3>\1</h3>', html_content, flags=re.MULTILINE)
    html_content = re.sub(r'^## (.+)$', r'<h2>\1</h2>', html_content, flags=re.MULTILINE)
    html_content = re.sub(r'^# (.+)$', r'<h1>\1</h1>', html_content, flags=re.MULTILINE)
    html_content = re.sub(r'^#### (.+)$', r'<h4>\1</h4>', html_content, flags=re.MULTILINE)
    
    # Bold and italic
    html_content = re.sub(r'\*\*\*(.+?)\*\*\*', r'<b><i>\1</i></b>', html_content)
    html_content = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', html_content)
    html_content = re.sub(r'\*(.+?)\*', r'<i>\1</i>', html_content)
    
    # Inline code
    html_content = re.sub(r'`(.+?)`', r'<code>\1</code>', html_content)
    
    # Code blocks
    html_content = re.sub(
        r'```(\w+)?\n(.*?)```',
        lambda m: f'<pre><code>{m.group(2)}</code></pre>',
        html_content,
        flags=re.DOTALL
    )
    
    # Tables
    lines = html_content.split('\n')
    new_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]
        # Check for table start
        if '|' in line and i + 1 < len(lines) and '|---' in lines[i + 1]:
            # Parse table
            headers = [cell.strip() for cell in line.split('|') if cell.strip()]
            i += 2  # Skip separator line
            rows = []
            while i < len(lines) and '|' in lines[i]:
                cells = [cell.strip() for cell in lines[i].split('|') if cell.strip()]
                if cells:
                    rows.append(cells)
                i += 1
            
            # Build HTML table
            table_html = '<table>\n<thead>\n<tr>'
            for h in headers:
                table_html += f'<th>{h}</th>'
            table_html += '</tr>\n</thead>\n<tbody>\n'
            for row in rows:
                table_html += '<tr>'
                for cell in row[:len(headers)]:
                    table_html += f'<td>{cell}</td>'
                table_html += '</tr>\n'
            table_html += '</tbody>\n</table>'
            new_lines.append(table_html)
        else:
            new_lines.append(line)
            i += 1
    
    html_content = '\n'.join(new_lines)
    
    # Lists
    # Unordered lists
    html_content = re.sub(r'^\s*[-*] (.+)$', r'<li>\1</li>', html_content, flags=re.MULTILINE)
    # Ordered lists  
    html_content = re.sub(r'^\s*(\d+)\.\s(.+)$', r'<li>\2</li>', html_content, flags=re.MULTILINE)
    
    # Wrap consecutive li elements in ul
    html_content = re.sub(r'(<li>.+</li>\n)+', r'<ul>\g<0></ul>', html_content)
    
    # Blockquotes
    html_content = re.sub(r'^&gt;\s*(.+)$', r'<blockquote>\1</blockquote>', html_content, flags=re.MULTILINE)
    
    # Horizontal rules
    html_content = re.sub(r'^---+$', r'<hr>', html_content, flags=re.MULTILINE)
    
    # Paragraphs (wrap non-tag lines)
    lines = html_content.split('\n')
    result = []
    in_para = False
    
    for line in lines:
        stripped = line.strip()
        if not stripped:
            if in_para:
                result.append('</p>')
                in_para = False
            result.append('')
        elif not re.match(r'<(h\d|ul|ol|li|table|blockquote|pre|hr|/|div)', stripped):
            if not in_para:
                result.append('<p>')
                in_para = True
            result.append(line)
        else:
            if in_para:
                result.append('</p>')
                in_para = False
            result.append(line)
    
    if in_para:
        result.append('</p>')
    
    html_content = '\n'.join(result)
    
    # Wrap in full HTML document
    full_html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@400;500;700&display=swap');
        
        * {{
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Noto Sans SC', -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Microsoft YaHei', sans-serif;
            line-height: 1.8;
            color: #333;
            max-width: 900px;
            margin: 0 auto;
            padding: 40px 20px;
            background: #fff;
        }}
        
        h1 {{
            color: #1a73e8;
            border-bottom: 3px solid #1a73e8;
            padding-bottom: 15px;
            margin-bottom: 30px;
            font-size: 28px;
            font-weight: 700;
        }}
        
        h2 {{
            color: #2c5aa0;
            margin-top: 40px;
            margin-bottom: 20px;
            font-size: 22px;
            font-weight: 600;
            border-left: 4px solid #2c5aa0;
            padding-left: 15px;
        }}
        
        h3 {{
            color: #444;
            margin-top: 30px;
            margin-bottom: 15px;
            font-size: 18px;
            font-weight: 600;
        }}
        
        h4 {{
            color: #555;
            margin-top: 20px;
            margin-bottom: 10px;
            font-size: 16px;
            font-weight: 600;
        }}
        
        p {{
            margin: 15px 0;
            text-align: justify;
        }}
        
        ul, ol {{
            margin: 15px 0;
            padding-left: 30px;
        }}
        
        li {{
            margin: 8px 0;
        }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            font-size: 14px;
        }}
        
        th, td {{
            padding: 12px;
            text-align: left;
            border: 1px solid #ddd;
        }}
        
        th {{
            background-color: #f5f7fa;
            font-weight: 600;
            color: #2c5aa0;
        }}
        
        tr:nth-child(even) {{
            background-color: #fafbfc;
        }}
        
        pre {{
            background-color: #f5f7fa;
            padding: 20px;
            border-radius: 8px;
            overflow-x: auto;
            font-family: 'Consolas', 'Monaco', monospace;
            font-size: 13px;
            line-height: 1.6;
            border: 1px solid #e1e4e8;
        }}
        
        code {{
            background-color: #f0f3f6;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: 'Consolas', 'Monaco', monospace;
            font-size: 90%;
            color: #e83e8c;
        }}
        
        pre code {{
            background: none;
            padding: 0;
            color: #333;
        }}
        
        blockquote {{
            border-left: 4px solid #1a73e8;
            margin: 20px 0;
            padding: 15px 20px;
            background-color: #f8f9fa;
            color: #555;
            font-style: italic;
        }}
        
        hr {{
            border: none;
            border-top: 2px solid #e1e4e8;
            margin: 30px 0;
        }}
        
        a {{
            color: #1a73e8;
            text-decoration: none;
        }}
        
        a:hover {{
            text-decoration: underline;
        }}
        
        strong {{
            color: #2c5aa0;
            font-weight: 600;
        }}
        
        /* Print styles */
        @media print {{
            body {{
                padding: 20px;
            }}
            
            h1 {{
                page-break-before: avoid;
            }}
            
            h2, h3 {{
                page-break-after: avoid;
            }}
            
            pre, table {{
                page-break-inside: avoid;
            }}
        }}
    </style>
</head>
<body>
{html_content}
</body>
</html>'''
    
    return full_html


def convert_file(md_file, html_file, title="文档"):
    """Convert Markdown file to HTML file"""
    with open(md_file, 'r', encoding='utf-8') as f:
        md_content = f.read()
    
    html = md_to_html(md_content, title)
    
    with open(html_file, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"HTML已生成: {html_file}")
    return html


if __name__ == '__main__':
    md_file = '/root/.openclaw/workspace/energy_storage/data/reports/系统架构综合报告_20260329.md'
    html_file = '/root/.openclaw/workspace/energy_storage/data/reports/系统架构综合报告_20260329.html'
    
    convert_file(md_file, html_file, "系统架构综合报告")
