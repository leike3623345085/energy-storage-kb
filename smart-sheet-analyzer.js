/**
 * 智能工作表分析器 - 自动识别表头、空白行、数据行
 */
class SmartSheetAnalyzer {
    constructor(worksheet) {
        this.worksheet = worksheet;
        this.maxScanRows = Math.min(50, worksheet.rowCount); // 最多扫描前50行
    }

    /**
     * 主分析方法 - 返回完整的结构信息
     */
    analyze() {
        const result = {
            headerRow: null,      // 表头行号
            blankRows: [],        // 空白行列表
            dataStartRow: null,   // 数据起始行
            dataEndRow: null,     // 数据结束行
            summaryRow: null,     // 汇总行
            structure: []         // 每行的类型分析
        };

        // 第一步：识别表头行
        result.headerRow = this._findHeaderRow();
        if (!result.headerRow) {
            return result;
        }

        // 第二步：分析表头下方的所有行
        const analysis = this._analyzeBelowHeader(result.headerRow);
        
        result.blankRows = analysis.blankRows;
        result.dataStartRow = analysis.dataStartRow;
        result.dataEndRow = analysis.dataEndRow;
        result.summaryRow = analysis.summaryRow;
        result.structure = analysis.structure;

        return result;
    }

    /**
     * 识别表头行 - 基于行特征评分
     */
    _findHeaderRow() {
        let bestRow = null;
        let bestScore = 0;

        for (let rowNum = 1; rowNum <= this.maxScanRows; rowNum++) {
            const row = this.worksheet.getRow(rowNum);
            const score = this._scoreAsHeader(row);

            if (score > bestScore) {
                bestScore = score;
                bestRow = rowNum;
            }
        }

        // 表头评分必须达到一定阈值
        return bestScore >= 3 ? bestRow : null;
    }

    /**
     * 评估一行作为表头的可能性
     */
    _scoreAsHeader(row) {
        let score = 0;
        let textCount = 0;
        let numberCount = 0;
        let dateCount = 0;
        let emptyCount = 0;
        let totalCells = 0;
        const textLengths = [];

        row.eachCell({ includeEmpty: true }, (cell) => {
            totalCells++;
            const value = cell.value;
            const type = this._getCellType(value);

            switch (type) {
                case 'text':
                    textCount++;
                    const text = String(value).trim();
                    if (text.length > 0 && text.length < 50) {
                        textLengths.push(text.length);
                    }
                    break;
                case 'number':
                    numberCount++;
                    break;
                case 'date':
                    dateCount++;
                    break;
                case 'empty':
                    emptyCount++;
                    break;
            }
        });

        if (totalCells === 0) return 0;

        const nonEmptyCells = totalCells - emptyCount;
        
        // 表头特征评分
        // 1. 文字比例高（+3分）
        if (textCount / nonEmptyCells > 0.7) {
            score += 3;
        }

        // 2. 数字比例低（+2分）
        if (numberCount / nonEmptyCells < 0.2) {
            score += 2;
        }

        // 3. 日期比例低（+1分）
        if (dateCount === 0) {
            score += 1;
        }

        // 4. 文字长度适中（表头通常是短文本）（+2分）
        if (textLengths.length > 0) {
            const avgLength = textLengths.reduce((a, b) => a + b, 0) / textLengths.length;
            if (avgLength >= 2 && avgLength <= 15) {
                score += 2;
            }
        }

        // 5. 非空单元格比例高（+1分）
        if (nonEmptyCells / totalCells > 0.5) {
            score += 1;
        }

        // 6. 检查是否包含常见的表头关键词（+2分）
        const headerKeywords = ['姓名', '名称', '日期', '金额', '数量', '序号', '编号', '合计', '总计'];
        let hasKeyword = false;
        row.eachCell((cell) => {
            const text = String(cell.value || '').trim();
            if (headerKeywords.some(kw => text.includes(kw))) {
                hasKeyword = true;
            }
        });
        if (hasKeyword) {
            score += 2;
        }

        return score;
    }

    /**
     * 分析表头下方的行结构
     */
    _analyzeBelowHeader(headerRowNum) {
        const result = {
            blankRows: [],
            dataStartRow: null,
            dataEndRow: null,
            summaryRow: null,
            structure: []
        };

        let consecutiveBlank = 0;
        let maxConsecutiveBlank = 2;
        let foundData = false;
        let lastDataRow = null;

        for (let rowNum = headerRowNum + 1; rowNum <= this.worksheet.rowCount; rowNum++) {
            const row = this.worksheet.getRow(rowNum);
            const rowType = this._classifyRow(row, headerRowNum);

            result.structure.push({
                rowNum,
                type: rowType.type,
                confidence: rowType.confidence,
                details: rowType.details
            });

            switch (rowType.type) {
                case 'blank':
                    result.blankRows.push(rowNum);
                    consecutiveBlank++;
                    
                    // 如果已经找到数据区，连续空白行表示数据结束
                    if (foundData && consecutiveBlank >= maxConsecutiveBlank) {
                        if (!result.dataEndRow) {
                            result.dataEndRow = lastDataRow;
                        }
                    }
                    break;

                case 'data':
                    if (!result.dataStartRow) {
                        result.dataStartRow = rowNum;
                    }
                    lastDataRow = rowNum;
                    foundData = true;
                    consecutiveBlank = 0;
                    
                    // 如果之前有空白行，现在遇到数据，之前的空白行不算真正的空白区
                    if (result.blankRows.length > 0 && !foundData) {
                        result.blankRows = [];
                    }
                    break;

                case 'summary':
                    result.summaryRow = rowNum;
                    // 汇总行通常表示数据结束
                    if (!result.dataEndRow && lastDataRow) {
                        result.dataEndRow = lastDataRow;
                    }
                    consecutiveBlank = 0;
                    break;

                case 'other':
                    consecutiveBlank = 0;
                    break;
            }
        }

        // 如果没找到数据结束行，默认到最后一行
        if (!result.dataEndRow && lastDataRow) {
            result.dataEndRow = lastDataRow;
        }

        return result;
    }

    /**
     * 分类单行类型
     */
    _classifyRow(row, headerRowNum) {
        const stats = {
            emptyCells: 0,
            textCells: 0,
            numberCells: 0,
            formulaCells: 0,
            totalCells: 0,
            hasSumKeyword: false,
            hasFormulaSum: false
        };

        row.eachCell({ includeEmpty: true }, (cell) => {
            stats.totalCells++;
            const type = this._getCellType(cell.value);

            switch (type) {
                case 'empty':
                    stats.emptyCells++;
                    break;
                case 'text':
                    stats.textCells++;
                    const text = String(cell.value || '').trim();
                    if (/合计|总计|汇总|小计|SUM/i.test(text)) {
                        stats.hasSumKeyword = true;
                    }
                    break;
                case 'number':
                    stats.numberCells++;
                    break;
            }

            // 检查公式
            if (cell.formula) {
                stats.formulaCells++;
                if (/SUM|AVERAGE|COUNT/i.test(cell.formula)) {
                    stats.hasFormulaSum = true;
                }
            }
        });

        const nonEmptyCells = stats.totalCells - stats.emptyCells;

        // 判断行类型
        // 1. 空白行
        if (nonEmptyCells === 0 || stats.emptyCells / stats.totalCells > 0.9) {
            return {
                type: 'blank',
                confidence: 0.95,
                details: { emptyRatio: stats.emptyCells / stats.totalCells }
            };
        }

        // 2. 汇总行特征
        if (stats.hasSumKeyword || stats.hasFormulaSum) {
            return {
                type: 'summary',
                confidence: 0.9,
                details: { hasSumKeyword: stats.hasSumKeyword, hasFormulaSum: stats.hasFormulaSum }
            };
        }

        // 3. 数据行特征：数字比例高，有公式
        if (stats.numberCells / nonEmptyCells > 0.3 || stats.formulaCells > 0) {
            return {
                type: 'data',
                confidence: 0.85,
                details: { numberRatio: stats.numberCells / nonEmptyCells, formulaCells: stats.formulaCells }
            };
        }

        // 4. 其他（可能是备注、说明等）
        return {
            type: 'other',
            confidence: 0.5,
            details: { textRatio: stats.textCells / nonEmptyCells }
        };
    }

    /**
     * 获取单元格类型
     */
    _getCellType(value) {
        if (value === null || value === undefined || value === '') {
            return 'empty';
        }
        if (value instanceof Date) {
            return 'date';
        }
        if (typeof value === 'number') {
            return 'number';
        }
        if (typeof value === 'string') {
            // 检查是否是日期字符串
            if (/^\d{4}[\-\/]\d{2}[\-\/]\d{2}/.test(value)) {
                return 'date';
            }
            return 'text';
        }
        if (typeof value === 'object') {
            // ExcelJS 的富文本、公式结果等
            if (value.text || value.result !== undefined) {
                return this._getCellType(value.text || value.result);
            }
        }
        return 'text';
    }

    /**
     * 生成分析报告（用于调试）
     */
    generateReport() {
        const analysis = this.analyze();
        
        let report = '=== 工作表结构分析报告 ===\n\n';
        report += `表头行: 第 ${analysis.headerRow} 行\n`;
        report += `空白行: ${analysis.blankRows.length > 0 ? analysis.blankRows.join(', ') : '无'}\n`;
        report += `数据起始行: 第 ${analysis.dataStartRow} 行\n`;
        report += `数据结束行: 第 ${analysis.dataEndRow} 行\n`;
        report += `汇总行: 第 ${analysis.summaryRow} 行\n\n`;
        
        report += '详细结构:\n';
        analysis.structure.forEach(item => {
            report += `  第 ${item.rowNum} 行: ${item.type} (置信度: ${item.confidence})\n`;
        });

        return report;
    }
}

/**
 * 使用示例 - 在 exportToExisting 中集成
 */
async function exportToExistingWithAutoDetect(columns) {
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

    // ★★★ 自动分析工作表结构 ★★★
    const analyzer = new SmartSheetAnalyzer(worksheet);
    const analysis = analyzer.analyze();

    console.log(analyzer.generateReport());

    // 使用自动检测的结果
    const headerRow = analysis.headerRow || 1;
    const dataStartRow = analysis.dataStartRow || (headerRow + 1);
    const dataEndRow = analysis.dataEndRow || (dataStartRow + 10);
    const summaryRow = analysis.summaryRow || (dataEndRow + 1);

    console.log(`自动识别结果: 表头=${headerRow}, 数据=${dataStartRow}-${dataEndRow}, 汇总=${summaryRow}`);

    // 后续逻辑与原有 exportToExisting 相同，使用自动检测的行号...
    // ... 原有填充逻辑
}

// 导出供外部使用
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { SmartSheetAnalyzer };
}
