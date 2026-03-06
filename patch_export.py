import re

with open('/root/.openclaw/workspace/WASM数据分析_自动识别版.html', 'r') as f:
    content = f.read()

# 找到 exportToExisting 函数中 worksheet 获取后的位置
old_code = '''    const worksheet = workbookToUse.getWorksheet(targetSheetName);
    if (!worksheet) {
        alert('找不到目标工作表');
        return;
    }'''

new_code = '''    const worksheet = workbookToUse.getWorksheet(targetSheetName);
    if (!worksheet) {
        alert('找不到目标工作表');
        return;
    }
    
    // ★★★ 自动分析工作表结构 ★★★
    console.log('开始自动分析工作表结构...');
    const analysis = autoAnalyzeSheet(worksheet);
    console.log('自动分析结果:', analysis);
    
    // 使用自动检测的结果（如果用户没有手动修改）
    const userStartRow = parseInt(document.getElementById('startRow').value);
    const userEndRow = parseInt(document.getElementById('endRow').value);
    const userSummaryRow = parseInt(document.getElementById('summaryRow').value);
    
    const startRow = userStartRow || analysis.dataStartRow;
    const endRow = userEndRow || analysis.dataEndRow;
    const summaryRow = userSummaryRow || analysis.summaryRow;
    
    // 更新输入框显示检测到的值（如果用户未设置）
    if (!userStartRow) document.getElementById('startRow').value = analysis.dataStartRow;
    if (!userEndRow) document.getElementById('endRow').value = analysis.dataEndRow;
    if (!userSummaryRow) document.getElementById('summaryRow').value = analysis.summaryRow;
    
    // 显示检测结果
    const mappingResult = document.getElementById('columnMappingResult');
    const mappingPanel = document.getElementById('columnMappingPanel');
    if (mappingResult && mappingPanel) {
        mappingResult.innerHTML = `
            <strong>✅ 自动识别成功</strong><br>
            表头行: 第${analysis.headerRow}行 | 
            数据: 第${analysis.dataStartRow}-${analysis.dataEndRow}行 | 
            汇总: 第${analysis.summaryRow}行
            ${analysis.blankRows.length > 0 ? '<br>空白行: 第' + analysis.blankRows.join(',') + '行' : ''}
        `;
        mappingPanel.style.display = 'block';
    }'''

if old_code in content:
    content = content.replace(old_code, new_code)
    with open('/root/.openclaw/workspace/WASM数据分析_自动识别版.html', 'w') as f:
        f.write(content)
    print('修改成功！')
else:
    print('未找到目标代码')