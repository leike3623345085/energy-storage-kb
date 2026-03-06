
// ==================== 智能工作表分析器（新增）====================

/**
 * 自动分析工作表结构，识别表头、空白行、数据行、汇总行
 */
function autoAnalyzeSheet(worksheet) {
    const maxScanRows = Math.min(50, worksheet.rowCount);
    
    function findHeaderRow() {
        let bestRow = null, bestScore = 0;
        for (let rowNum = 1; rowNum <= maxScanRows; rowNum++) {
            const row = worksheet.getRow(rowNum);
            const score = scoreAsHeader(row);
            if (score > bestScore) { bestScore = score; bestRow = rowNum; }
        }
        return bestScore >= 3 ? bestRow : 1;
    }

    function scoreAsHeader(row) {
        let score = 0, textCount = 0, numberCount = 0, dateCount = 0, emptyCount = 0;
        let totalCells = 0;
        const textLengths = [];

        row.eachCell({ includeEmpty: true }, (cell) => {
            totalCells++;
            const type = getCellType(cell.value);
            if (type === 'text') {
                textCount++;
                const text = String(cell.value).trim();
                if (text.length > 0 && text.length < 50) textLengths.push(text.length);
            } else if (type === 'number') numberCount++;
            else if (type === 'date') dateCount++;
            else if (type === 'empty') emptyCount++;
        });

        if (totalCells === 0) return 0;
        const nonEmpty = totalCells - emptyCount;
        if (textCount / nonEmpty > 0.7) score += 3;
        if (numberCount / nonEmpty < 0.2) score += 2;
        if (dateCount === 0) score += 1;
        if (textLengths.length > 0) {
            const avg = textLengths.reduce((a, b) => a + b, 0) / textLengths.length;
            if (avg >= 2 && avg <= 15) score += 2;
        }
        if (nonEmpty / totalCells > 0.5) score += 1;
        
        const keywords = ['姓名', '名称', '日期', '金额', '数量', '序号', '编号', '合计', '总计'];
        let hasKeyword = false;
        row.eachCell((cell) => {
            const text = String(cell.value || '').trim();
            if (keywords.some(kw => text.includes(kw))) hasKeyword = true;
        });
        if (hasKeyword) score += 2;
        return score;
    }

    function analyzeBelowHeader(headerRowNum) {
        const result = { blankRows: [], dataStartRow: null, dataEndRow: null, summaryRow: null };
        let consecutiveBlank = 0, foundData = false, lastDataRow = null;

        for (let rowNum = headerRowNum + 1; rowNum <= worksheet.rowCount; rowNum++) {
            const row = worksheet.getRow(rowNum);
            const type = classifyRow(row);
            switch (type) {
                case 'blank':
                    result.blankRows.push(rowNum);
                    consecutiveBlank++;
                    if (foundData && consecutiveBlank >= 2 && !result.dataEndRow) result.dataEndRow = lastDataRow;
                    break;
                case 'data':
                    if (!result.dataStartRow) result.dataStartRow = rowNum;
                    lastDataRow = rowNum; foundData = true; consecutiveBlank = 0;
                    break;
                case 'summary':
                    result.summaryRow = rowNum;
                    if (!result.dataEndRow && lastDataRow) result.dataEndRow = lastDataRow;
                    consecutiveBlank = 0;
                    break;
                default:
                    consecutiveBlank = 0;
            }
        }
        if (!result.dataEndRow && lastDataRow) result.dataEndRow = lastDataRow;
        if (!result.dataStartRow) result.dataStartRow = headerRowNum + 1;
        if (!result.dataEndRow) result.dataEndRow = result.dataStartRow + 9;
        if (!result.summaryRow) result.summaryRow = result.dataEndRow + 1;
        return result;
    }

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
            } else if (type === 'number') number++;
            if (cell.formula) {
                formula++;
                if (/SUM|AVERAGE|COUNT/i.test(cell.formula)) hasSumFormula = true;
            }
        });
        const nonEmpty = total - empty;
        if (nonEmpty === 0 || empty / total > 0.9) return 'blank';
        if (hasSumKeyword || hasSumFormula) return 'summary';
        if (number / nonEmpty > 0.3 || formula > 0) return 'data';
        return 'other';
    }

    function getCellType(value) {
        if (value === null || value === undefined || value === '') return 'empty';
        if (value instanceof Date) return 'date';
        if (typeof value === 'number') return 'number';
        if (typeof value === 'string') {
            if (/^\d{4}[\-/]\d{2}[\-/]\d{2}/.test(value)) return 'date';
            return 'text';
        }
        if (typeof value === 'object') {
            if (value.text || value.result !== undefined) return getCellType(value.text || value.result);
        }
        return 'text';
    }

    const headerRow = findHeaderRow();
    const below = analyzeBelowHeader(headerRow);
    return { headerRow, ...below };
}

// ==================== 智能工作表分析器（结束）====================

