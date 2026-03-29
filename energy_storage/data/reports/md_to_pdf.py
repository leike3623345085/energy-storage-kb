#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Markdown to PDF Converter using fpdf2 - Fixed Version
"""

from fpdf import FPDF, XPos, YPos
import re
import os

class PDF(FPDF):
    def header(self):
        if self.page_no() > 1:
            self.set_font('SIMSUN', '', 8)
            self.set_text_color(128, 128, 128)
            self.cell(0, 10, '系统架构综合报告', 0, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')
            self.set_draw_color(200, 200, 200)
            self.line(10, 20, 200, 20)
            self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font('SIMSUN', '', 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f'第 {self.page_no()} 页', 0, align='C')

def parse_markdown(md_content):
    """解析Markdown内容"""
    lines = md_content.split('\n')
    elements = []
    
    i = 0
    while i < len(lines):
        line = lines[i]
        
        if line.startswith('# '):
            elements.append(('h1', line[2:].strip()))
        elif line.startswith('## '):
            elements.append(('h2', line[3:].strip()))
        elif line.startswith('### '):
            elements.append(('h3', line[4:].strip()))
        elif line.startswith('#### '):
            elements.append(('h4', line[5:].strip()))
        elif line.startswith('```'):
            code_lines = []
            i += 1
            while i < len(lines) and not lines[i].startswith('```'):
                code_lines.append(lines[i])
                i += 1
            elements.append(('code', '\n'.join(code_lines)))
        elif '|' in line and i + 1 < len(lines) and '|---' in lines[i + 1]:
            table_lines = [line]
            i += 1
            while i < len(lines) and '|' in lines[i]:
                table_lines.append(lines[i])
                i += 1
            elements.append(('table', table_lines))
            continue
        elif any(c in line for c in ['┌', '├', '└', '│', '─', '┬', '┼', '┴']):
            diagram_lines = [line]
            i += 1
            while i < len(lines) and (any(c in lines[i] for c in ['┌', '├', '└', '│', '─', '┬', '┼', '┴', '▶', '▼']) or lines[i].strip() == ''):
                if lines[i].strip() != '' or (diagram_lines and diagram_lines[-1].strip() != ''):
                    diagram_lines.append(lines[i])
                i += 1
            elements.append(('diagram', '\n'.join(diagram_lines)))
            continue
        elif line.strip().startswith('- ') or line.strip().startswith('* '):
            text = line.strip()[2:].strip()
            text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
            text = re.sub(r'`(.+?)`', r'\1', text)
            elements.append(('list', text))
        elif re.match(r'^\d+\.\s', line.strip()):
            text = re.sub(r'^(\d+)\.\s*', r'[\1] ', line.strip())
            text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
            elements.append(('olist', text))
        elif line.strip().startswith('>'):
            elements.append(('quote', line.strip()[1:].strip()))
        elif line.strip() == '---' or line.strip() == '***':
            elements.append(('hr', ''))
        elif line.strip():
            text = line.strip()
            text = re.sub(r'\*\*\*(.+?)\*\*\*', r'\1', text)
            text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
            text = re.sub(r'\*(.+?)\*', r'\1', text)
            text = re.sub(r'`(.+?)`', r'\1', text)
            elements.append(('p', text))
        
        i += 1
    
    return elements

def generate_pdf(md_file, pdf_file):
    """生成PDF文件"""
    pdf = PDF()
    
    # 添加中文字体 - 使用系统字体
    font_paths = [
        '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',
        '/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc',
        '/usr/share/fonts/truetype/wqy/wqy-microhei.ttc',
        '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
    ]
    
    font_loaded = False
    for font_path in font_paths:
        if os.path.exists(font_path):
            try:
                pdf.add_font('SIMSUN', '', font_path)
                pdf.add_font('SIMHEI', '', font_path)
                font_loaded = True
                print(f"使用字体: {font_path}")
                break
            except:
                continue
    
    if not font_loaded:
        print("警告: 未找到中文字体，使用默认字体")
        pdf.add_font('SIMSUN', '', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')
        pdf.add_font('SIMHEI', '', '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf')
    
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    # 读取Markdown内容
    with open(md_file, 'r', encoding='utf-8') as f:
        md_content = f.read()
    
    elements = parse_markdown(md_content)
    
    for elem_type, content in elements:
        try:
            if elem_type == 'h1':
                pdf.set_font('SIMHEI', '', 16)
                pdf.set_text_color(0, 51, 102)
                pdf.ln(8)
                pdf.cell(0, 10, content, 0, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                pdf.set_draw_color(0, 51, 102)
                pdf.line(10, pdf.get_y() - 2, 80, pdf.get_y() - 2)
                pdf.ln(5)
            
            elif elem_type == 'h2':
                pdf.set_font('SIMHEI', '', 13)
                pdf.set_text_color(0, 102, 153)
                pdf.ln(6)
                pdf.cell(0, 8, content, 0, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                pdf.ln(2)
            
            elif elem_type == 'h3':
                pdf.set_font('SIMHEI', '', 11)
                pdf.set_text_color(51, 51, 51)
                pdf.ln(4)
                pdf.cell(0, 6, content, 0, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            
            elif elem_type == 'h4':
                pdf.set_font('SIMHEI', '', 10)
                pdf.set_text_color(68, 68, 68)
                pdf.ln(2)
                pdf.cell(0, 5, content, 0, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            
            elif elem_type == 'p':
                pdf.set_font('SIMSUN', '', 10)
                pdf.set_text_color(50, 50, 50)
                pdf.multi_cell(0, 5, content)
                pdf.ln(2)
            
            elif elem_type == 'list':
                pdf.set_font('SIMSUN', '', 10)
                pdf.set_text_color(50, 50, 50)
                # 使用 write 而不是 cell，避免宽度限制问题
                pdf.write(5, '  • ')
                pdf.write(5, content)
                pdf.ln(5)
            
            elif elem_type == 'olist':
                pdf.set_font('SIMSUN', '', 10)
                pdf.set_text_color(50, 50, 50)
                pdf.write(5, '  ' + content)
                pdf.ln(5)
            
            elif elem_type == 'code':
                render_code(pdf, content)
            
            elif elem_type == 'diagram':
                render_diagram(pdf, content)
            
            elif elem_type == 'table':
                render_table(pdf, content)
            
            elif elem_type == 'hr':
                pdf.set_draw_color(200, 200, 200)
                pdf.line(10, pdf.get_y(), 200, pdf.get_y())
                pdf.ln(3)
        
        except Exception as e:
            print(f"渲染元素失败 ({elem_type}): {e}")
            continue
    
    pdf.output(pdf_file)
    print(f"PDF已生成: {pdf_file}")

def render_code(pdf, code):
    """渲染代码块"""
    pdf.set_fill_color(245, 245, 245)
    pdf.set_draw_color(220, 220, 220)
    pdf.set_font('SIMSUN', '', 7)
    pdf.set_text_color(80, 80, 80)
    
    lines = code.split('\n')
    if len(lines) > 30:
        lines = lines[:30] + ['... (代码已截断)']
    
    for line in lines:
        if pdf.get_y() > 270:
            pdf.add_page()
        pdf.cell(0, 4, line[:90], 0, new_x=XPos.LMARGIN, new_y=YPos.NEXT, fill=True)
    
    pdf.ln(3)

def render_diagram(pdf, diagram):
    """渲染ASCII图表"""
    pdf.set_fill_color(250, 250, 252)
    pdf.set_font('SIMSUN', '', 6)
    pdf.set_text_color(60, 60, 80)
    
    lines = diagram.split('\n')
    if len(lines) > 40:
        lines = lines[:40] + ['... (图表已截断)']
    
    for line in lines:
        if pdf.get_y() > 275:
            pdf.add_page()
        display_line = line[:110] if len(line) > 110 else line
        pdf.cell(0, 3, display_line, 0, new_x=XPos.LMARGIN, new_y=YPos.NEXT, fill=True)
    
    pdf.ln(3)

def render_table(pdf, table_lines):
    """渲染表格"""
    if len(table_lines) < 2:
        return
    
    headers = [cell.strip() for cell in table_lines[0].split('|') if cell.strip()]
    
    rows = []
    for line in table_lines[2:]:
        cells = [cell.strip() for cell in line.split('|') if cell.strip()]
        if cells:
            rows.append(cells)
    
    if not rows:
        return
    
    col_count = min(len(headers), 6)  # 最多6列
    col_width = 180 / col_count
    
    pdf.set_fill_color(240, 240, 240)
    pdf.set_font('SIMHEI', '', 8)
    pdf.set_text_color(50, 50, 50)
    
    for header in headers[:col_count]:
        pdf.cell(col_width, 5, header[:12], 1, fill=True)
    pdf.ln()
    
    pdf.set_fill_color(255, 255, 255)
    pdf.set_font('SIMSUN', '', 7)
    
    for row in rows[:15]:  # 最多15行
        for i, cell in enumerate(row[:col_count]):
            cell_text = re.sub(r'\*\*(.+?)\*\*', r'\1', cell)
            pdf.cell(col_width, 4, cell_text[:15], 1)
        pdf.ln()
    
    if len(rows) > 15:
        pdf.cell(180, 4, f'... 还有 {len(rows) - 15} 行数据', 0)
        pdf.ln()
    
    pdf.ln(3)

if __name__ == '__main__':
    md_file = '/root/.openclaw/workspace/energy_storage/data/reports/系统架构综合报告_20260329.md'
    pdf_file = '/root/.openclaw/workspace/energy_storage/data/reports/系统架构综合报告_20260329.pdf'
    
    generate_pdf(md_file, pdf_file)
