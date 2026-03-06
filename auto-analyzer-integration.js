/**
 * 智能工作表分析器 - 直接集成到 WASM数据分析.html
 * 在 exportToExisting 函数之前添加此代码
 */

/**
 * 自动分析工作表结构，识别表头、空白行、数据行、汇总行
 */
function autoAnalyzeSheet(worksheet) {
    const maxScanRows = Math.min(50, worksheet.rowCount);
    
    // 1. 识别表头行
    function findHeaderRow() {
        let bestRow = null;
        let bestScore = 0;

        for (let rowNum = 1; rowNum <= maxScanRows; rowNum++) {
            const row = worksheet.getRow(rowNum);
            const score = scoreAsHeader(row);
            
            if (score > bestScore) {
                bestScore = score;
                bestRow = rowNum;
            }
        }
        
        return bestScore >= 3 ? bestRow : 1; // 默认第一行
    }

    // 评估行作为表头的可能性
    function scoreAsHeader(row) {
        let score = 0;
        let textCount = 0, numberCount = 0, dateCount = 0, emptyCount = 0;
        let totalCells = 0;
        const textLengths = [];

        row.eachCell({ includeEmpty: true }, (cell) => {
            totalCells++;
            const value = cell.value;
            const type = getCellType(value);

            if (type === 'text') {
                textCount++;
                const text = String(value).trim();
                if (text.length > 0 && text.length < 50) {
                    textLengths.push(text.length);
                }
            } else if (type === 'number') {
                numberCount++;
            } else if (type === 'date') {
                dateCount++;
            } else if (type === 'empty') {
                emptyCount++;
            }
        });

        if (totalCells === 0) return 0;
        const nonEmpty = totalCells - emptyCount;

        // 表头特征评分
        if (textCount / nonEmpty > 0.7) score += 3;
        if (numberCount / nonEmpty < 0.2) score += 2;
        if (dateCount === 0) score += 1;
        
        if (textLengths.length > 0) {
            const avg = textLengths.reduce((a, b) => a + b, 0) / textLengths.length;
            if (avg >= 2 && avg <= 15) score += 2;
        }
        
        if (nonEmpty / totalCells > 0.5) score += 1;

        // 关键词检测
        const keywords = ['姓名', '名称', '日期', '金额', '数量', '序号', '编号', '合计', '总计'];
        let hasKeyword = false;
        row.eachCell((cell) => {
            const text = String(cell.value || '').trim();
            if (keywords.some(kw => text.includes(kw))) hasKeyword = true;
        });
        if (hasKeyword) score += 2;

        return score;
    }

    // 2. 分析表头下方的行
    function analyzeBelowHeader(headerRowNum) {
        const result = {
            blankRows: [],
            dataStartRow: null,
            dataEndRow: null,
            summaryRow: null
        };

        let consecutiveBlank = 0;
        let foundData = false;
        let lastDataRow = null;

        for (let rowNum = headerRowNum + 1; rowNum <= worksheet.rowCount; rowNum++) {
            const row = worksheet.getRow(rowNum);
            const type = classifyRow(row);

            switch (type) {
                case 'blank':
                    result.blankRows.push(rowNum);
                    consecutiveBlank++;
                    if (foundData && consecutiveBlank >= 2 && !result.dataEndRow) {
                        result.dataEndRow = lastDataRow;
                    }
                    break;
                    
                case 'data':
                    if (!result.dataStartRow) result.dataStartRow = rowNum;
                    lastDataRow = rowNum;
                    foundData = true;
                    consecutiveBlank = 0;
                    break;
                    
                case 'summary':
                    result.summaryRow = rowNum;
                    if (!result.dataEndRow && lastDataRow) {
                        result.dataEndRow = lastDataRow;
                    }
                    consecutiveBlank = 0;
                    break;
                    
                default:
                    consecutiveBlank = 0;
            }
        }

        if (!result.dataEndRow && lastDataRow) {
            result.dataEndRow = lastDataRow;
        }
        if (!result.dataStartRow) {
            result.dataStartRow = headerRowNum + 1;
        }
        if (!result.dataEndRow) {
            result.dataEndRow = result.dataStartRow + 9; // 默认10行
        }
        if (!result.summaryRow) {
            result.summaryRow = result.dataEndRow + 1;
        }

        return result;
    }

    // 分类单行类型
    function classifyRow(row) {
        let empty = 0, text = 0, number = 0, formula = 0, total = 0;
        let hasSumKeyword = false, hasSumFormula = false;

        row.eachCell({ includeEmpty: true }, (cell) => {
            total++;
            const type = getCellType(cell.value);
            
            if (type === 'empty') empty++;
            else if (type === 'text') {
                text++;
                const str = String(cell.value || '').trim();
                if (/合计|总计|汇总|小计|SUM/i.test(str)) hasSumKeyword = true;
            }
            else if (type === 'number') number++;

            if (cell.formula) {
                formula++;
                if (/SUM|AVERAGE|COUNT/i.test(cell.formula)) hasSumFormula = true;
            }
        });

        const nonEmpty = total - empty;

        // 空白行
        if (nonEmpty === 0 || empty / total > 0.9) return 'blank';
        
        // 汇总行
        if (hasSumKeyword || hasSumFormula) return 'summary';
        
        // 数据行
        if (number / nonEmpty > 0.3 || formula > 0) return 'data';
        
        return 'other';
    }

    // 获取单元格类型
    function getCellType(value) {
        if (value === null || value === undefined || value === '') return 'empty';
        if (value instanceof Date) return 'date';
        if (typeof value === 'number') return 'number';
        if (typeof value === 'string') {
            if (/^\d{4}[\-\/]\d{2}[\-\/]\d{2}/.test(value)) return 'date';
            return 'text';
        }
        if (typeof value === 'object') {
            if (value.text || value.result !== undefined) {
                return getCellType(value.text || value.result);
            }
        }
        return 'text';
    }

    // 执行分析
    const headerRow = findHeaderRow();
    const below = analyzeBelowHeader(headerRow);

    return {
        headerRow,
        ...below
    };
}

/**
 * 修改后的 exportToExisting 函数 - 支持自动检测
 */
async function exportToExistingAuto(columns) {
    const targetSheetName = document.getElementById('targetSheet').value;
    
    if (!targetSheetName) {
        alert('请选择目标工作表');
        return;
    }

    const workbookToUse = targetWorkbook || excelWorkbook;
    if (!workbookToUse) {
        alert('请先上传目标文件');
        return;
    }
    
    const worksheet = workbookToUse.getWorksheet(targetSheetName);
    if (!worksheet) {
        alert('找不到目标工作表');
        return;
    }

    // 自动分析工作表结构
    console.log('开始自动分析工作表结构...');
    const analysis = autoAnalyzeSheet(worksheet);
    
    console.log('自动分析结果:', {
        表头行: analysis.headerRow,
        空白行: analysis.blankRows,
        数据起始行: analysis.dataStartRow,
        数据结束行: analysis.dataEndRow,
        汇总行: analysis.summaryRow
    });

    // 使用自动检测的结果
    const startRow = analysis.dataStartRow;
    const endRow = analysis.dataEndRow;
    const summaryRow = analysis.summaryRow;

    // 后续逻辑与原有 exportToExisting 相同...
    // 调用原有的填充逻辑，传入自动检测的参数
    return await exportToExistingWithParams(columns, startRow, endRow, summaryRow);
}

/**
 * 带参数的导出函数（从原有 exportToExisting 提取）
 */
async function exportToExistingWithParams(columns, startRow, endRow, summaryRow) {
    const targetSheetName = document.getElementById('targetSheet').value;
    const workbookToUse = targetWorkbook || excelWorkbook;
    const worksheet = workbookToUse.getWorksheet(targetSheetName);
    
    const sortedColumns = [...columns].sort((a, b) => a.order - b.order);
    const dataToExport = matchedData;
    
    if (dataToExport.length === 0) {
        alert('没有数据可导出');
        return;
    }
    
    // 计算实际需要的行数
    let actualEndRow = startRow + dataToExport.length - 1;
    const originalEndRow = endRow;
    let shiftCount = actualEndRow - originalEndRow;
    
    console.log(`导出配置: 起始=${startRow}, 原结束=${originalEndRow}, 新结束=${actualEndRow}, 下移=${shiftCount}, 汇总行=${summaryRow}`);
    
    const maxCol = Math.max(worksheet.columnCount || 20, 50);
    
    // 设置第4行时间为当前系统时间
    const row4 = worksheet.getRow(4);
    const now = new Date();
    const dateStr = now.toLocaleDateString('zh-CN');
    row4.getCell(3).value = dateStr;
    row4.getCell(4).value = dateStr;
    console.log(`设置第4行时间: C列=${dateStr}, D列=${dateStr}`);
    row4.commit();
    
    // 保存汇总行及以下的所有内容和样式
    const savedRows = [];
    const saveStartRow = summaryRow;
    const maxRow = Math.max(worksheet.rowCount, summaryRow + 50);
    
    console.log(`保存 ${saveStartRow} 到 ${maxRow} 行的数据`);
    
    for (let i = saveStartRow; i <= maxRow; i++) {
        const sourceRow = worksheet.getRow(i);
        const rowData = {
            rowIndex: i,
            height: sourceRow.height,
            hidden: sourceRow.hidden,
            cells: []
        };
        
        for (let col = 1; col <= maxCol; col++) {
            const cell = sourceRow.getCell(col);
            rowData.cells.push({
                value: cell.value,
                style: cell.style ? JSON.parse(JSON.stringify(cell.style)) : null,
                numFmt: cell.numFmt,
                formula: cell.formula,
                result: cell.result
            });
        }
        
        savedRows.push(rowData);
    }
    
    // 保存合并单元格
    const savedMerges = [];
    if (worksheet._merges) {
        Object.keys(worksheet._merges).forEach(key => {
            const merge = worksheet._merges[key];
            if (merge.top >= summaryRow) {
                savedMerges.push({
                    top: merge.top,
                    left: merge.left,
                    bottom: merge.bottom,
                    right: merge.right,
                    key: key
                });
            }
        });
    }
    
    // 批量插入数据
    const rowsNeeded = dataToExport.length;
    const existingRows = originalEndRow - startRow + 1;
    
    // 检查是否有列映射
    if (Object.keys(columnMapping).length === 0) {
        buildColumnMapping();
    }
    
    // 填充数据函数
    function fillRowWithMapping(row, item, sortedColumns, rowIndex) {
        if (rowIndex === summaryRow) {
            console.log(`跳过汇总行 ${rowIndex}`);
            return;
        }
        
        const mappedTargetCols = Object.values(columnMapping);
        mappedTargetCols.forEach(col => {
            row.getCell(col).value = null;
        });
        
        sortedColumns.forEach((col) => {
            if (col.source === 'primary' && columnMapping[col.index]) {
                const value = item.primaryRow[col.index];
                const targetCol = columnMapping[col.index];
                
                const cell = row.getCell(targetCol);
                cell.value = value;
                
                cell.style = {
                    border: {
                        top: { style: 'thin' },
                        bottom: { style: 'thin' },
                        left: { style: 'thin' },
                        right: { style: 'thin' }
                    },
                    alignment: {
                        horizontal: 'center',
                        vertical: 'center'
                    }
                };
            }
        });
    }
    
    if (rowsNeeded > existingRows) {
        const rowsToInsert = rowsNeeded - existingRows;
        console.log(`需要插入 ${rowsToInsert} 行新行`);
        
        const templateRow = worksheet.getRow(startRow);
        const rowHeight = templateRow.height || 15;
        
        // 填充原数据行
        for (let i = 0; i < existingRows; i++) {
            const rowIndex = startRow + i;
            const row = worksheet.getRow(rowIndex);
            const item = dataToExport[i];
            
            fillRowWithMapping(row, item, sortedColumns, rowIndex);
            row.height = rowHeight;
            row.commit();
        }
        
        // 准备剩余数据行
        const mappedTargetCols = Object.values(columnMapping);
        const maxMappedCol = mappedTargetCols.length > 0 ? Math.max(...mappedTargetCols) : sortedColumns.length;
        
        const remainingData = dataToExport.slice(existingRows).map(item => {
            const rowData = new Array(maxMappedCol).fill('');
            sortedColumns.forEach((col) => {
                if (col.source === 'primary' && columnMapping[col.index]) {
                    const value = item.primaryRow[col.index];
                    const targetCol = columnMapping[col.index] - 1;
                    
                    if (targetCol >= 0 && targetCol < maxMappedCol) {
                        rowData[targetCol] = value;
                    }
                }
            });
            return rowData;
        });
        
        // 插入新行
        worksheet.spliceRows(originalEndRow + 1, 0, ...remainingData);
        
        // 设置插入行的样式
        for (let i = 0; i < remainingData.length; i++) {
            const rowIndex = originalEndRow + 1 + i;
            const row = worksheet.getRow(rowIndex);
            row.height = rowHeight;
            
            sortedColumns.forEach((col) => {
                if (col.source === 'primary' && columnMapping[col.index]) {
                    const targetCol = columnMapping[col.index];
                    const cell = row.getCell(targetCol);
                    cell.style = {
                        border: {
                            top: { style: 'thin' },
                            bottom: { style: 'thin' },
                            left: { style: 'thin' },
                            right: { style: 'thin' }
                        },
                        alignment: {
                            horizontal: 'center',
                            vertical: 'center'
                        }
                    };
                }
            });
            
            row.commit();
        }
        
        actualEndRow = startRow + rowsNeeded - 1;
        shiftCount = rowsToInsert;
    } else {
        console.log(`直接填充数据到 ${startRow} 到 ${actualEndRow} 行`);
        
        const templateRow = worksheet.getRow(startRow);
        const rowHeight = templateRow.height || 15;
        
        for (let i = 0; i < dataToExport.length; i++) {
            const rowIndex = startRow + i;
            const row = worksheet.getRow(rowIndex);
            const item = dataToExport[i];
            
            fillRowWithMapping(row, item, sortedColumns, rowIndex);
            row.height = rowHeight;
            row.commit();
        }
    }

    // 恢复保存的数据（下移后的位置）
    if (rowsNeeded > existingRows) {
        console.log(`恢复数据到新位置（下移 ${shiftCount} 行）`);
        
        const newSummaryRow = actualEndRow + 1;
        
        for (const savedRow of savedRows) {
            const newRowIndex = savedRow.rowIndex + shiftCount;
            const targetRow = worksheet.getRow(newRowIndex);
            
            targetRow.height = savedRow.height;
            targetRow.hidden = savedRow.hidden;
            
            for (let col = 1; col <= maxCol; col++) {
                const cellData = savedRow.cells[col - 1];
                const targetCell = targetRow.getCell(col);
                
                if (cellData.style) {
                    targetCell.style = cellData.style;
                }
                if (cellData.numFmt) {
                    targetCell.numFmt = cellData.numFmt;
                }
                
                if (newRowIndex === newSummaryRow) {
                    if (cellData.formula) {
                        const adjustedFormula = adjustFormulaRowRef(cellData.formula, shiftCount);
                        targetCell.value = { formula: adjustedFormula, result: cellData.result };
                    } else if (cellData.value !== null && cellData.value !== undefined) {
                        targetCell.value = cellData.value;
                    }
                } else {
                    if (cellData.formula) {
                        const adjustedFormula = adjustFormulaRowRef(cellData.formula, shiftCount);
                        targetCell.value = { formula: adjustedFormula, result: cellData.result };
                    } else if (cellData.value !== null && cellData.value !== undefined) {
                        targetCell.value = cellData.value;
                    }
                }
            }
            
            targetRow.commit();
        }
        
        // 重建合并单元格
        console.log(`重建 ${savedMerges.length} 个合并单元格`);
        
        if (worksheet._merges) {
            const mergesToUnmerge = [];
            Object.keys(worksheet._merges).forEach(key => {
                const m = worksheet._merges[key];
                if (m.top >= newSummaryRow) {
                    mergesToUnmerge.push(key);
                }
            });
            
            mergesToUnmerge.forEach(key => {
                try {
                    worksheet.unMergeCells(key);
                } catch(e) {}
            });
        }
        
        savedMerges.forEach(merge => {
            const newTop = merge.top + shiftCount;
            const newBottom = merge.bottom + shiftCount;
            
            try {
                worksheet.mergeCells(newTop, merge.left, newBottom, merge.right);
            } catch(e) {}
        });
    }
    
    // 调整公式中的行号引用
    function adjustFormulaRowRef(formula, offset) {
        if (!formula) return formula;
        return formula.replace(/(\$?[A-Z]+)(\$?)(\d+)/g, (match, col, dollar, row) => {
            const rowNum = parseInt(row.replace('$', ''));
            const newRow = rowNum + offset;
            return col + (row.includes('$') ? '$' : '') + newRow;
        });
    }
    
    // 下载文件
    const buffer = await workbookToUse.xlsx.writeBuffer();
    downloadExcel(buffer, `填充结果_${new Date().toLocaleDateString('zh-CN')}.xlsx`);
}
