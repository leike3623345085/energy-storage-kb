/**
 * 集成测试 - 测试多个组件协同工作
 * 测试不同分析器实现之间的一致性
 */

import { describe, it, expect, beforeEach } from 'vitest';
import { createMockWorksheet, TestTemplates } from '../mocks/exceljs.mock.js';

// 加载 SmartSheetAnalyzer
const loadSmartSheetAnalyzer = async () => {
  const code = `
    class SmartSheetAnalyzer {
      constructor(worksheet) {
        this.worksheet = worksheet;
        this.maxScanRows = Math.min(50, worksheet.rowCount);
      }

      analyze() {
        const result = {
          headerRow: null,
          blankRows: [],
          dataStartRow: null,
          dataEndRow: null,
          summaryRow: null,
          structure: []
        };

        result.headerRow = this._findHeaderRow();
        if (!result.headerRow) {
          return result;
        }

        const analysis = this._analyzeBelowHeader(result.headerRow);
        result.blankRows = analysis.blankRows;
        result.dataStartRow = analysis.dataStartRow;
        result.dataEndRow = analysis.dataEndRow;
        result.summaryRow = analysis.summaryRow;
        result.structure = analysis.structure;

        return result;
      }

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

        return bestScore >= 3 ? bestRow : null;
      }

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
        
        if (textCount / nonEmptyCells > 0.7) score += 3;
        if (numberCount / nonEmptyCells < 0.2) score += 2;
        if (dateCount === 0) score += 1;
        
        if (textLengths.length > 0) {
          const avgLength = textLengths.reduce((a, b) => a + b, 0) / textLengths.length;
          if (avgLength >= 2 && avgLength <= 15) score += 2;
        }
        
        if (nonEmptyCells / totalCells > 0.5) score += 1;

        const headerKeywords = ['姓名', '名称', '日期', '金额', '数量', '序号', '编号', '合计', '总计'];
        let hasKeyword = false;
        row.eachCell((cell) => {
          const text = String(cell.value || '').trim();
          if (headerKeywords.some(kw => text.includes(kw))) hasKeyword = true;
        });
        if (hasKeyword) score += 2;

        return score;
      }

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
              if (foundData && consecutiveBlank >= maxConsecutiveBlank) {
                if (!result.dataEndRow) result.dataEndRow = lastDataRow;
              }
              break;

            case 'data':
              if (!result.dataStartRow) result.dataStartRow = rowNum;
              lastDataRow = rowNum;
              foundData = true;
              consecutiveBlank = 0;
              if (result.blankRows.length > 0 && !foundData) result.blankRows = [];
              break;

            case 'summary':
              result.summaryRow = rowNum;
              if (!result.dataEndRow && lastDataRow) result.dataEndRow = lastDataRow;
              consecutiveBlank = 0;
              break;

            case 'other':
              consecutiveBlank = 0;
              break;
          }
        }

        if (!result.dataEndRow && lastDataRow) result.dataEndRow = lastDataRow;

        return result;
      }

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
              if (/合计|总计|汇总|小计|SUM/i.test(text)) stats.hasSumKeyword = true;
              break;
            case 'number':
              stats.numberCells++;
              break;
          }

          if (cell.formula) {
            stats.formulaCells++;
            if (/SUM|AVERAGE|COUNT/i.test(cell.formula)) stats.hasFormulaSum = true;
          }
        });

        const nonEmptyCells = stats.totalCells - stats.emptyCells;

        if (nonEmptyCells === 0 || stats.emptyCells / stats.totalCells > 0.9) {
          return {
            type: 'blank',
            confidence: 0.95,
            details: { emptyRatio: stats.emptyCells / stats.totalCells }
          };
        }

        if (stats.hasSumKeyword || stats.hasFormulaSum) {
          return {
            type: 'summary',
            confidence: 0.9,
            details: { hasSumKeyword: stats.hasSumKeyword, hasFormulaSum: stats.hasFormulaSum }
          };
        }

        if (stats.numberCells / nonEmptyCells > 0.3 || stats.formulaCells > 0) {
          return {
            type: 'data',
            confidence: 0.85,
            details: { numberRatio: stats.numberCells / nonEmptyCells, formulaCells: stats.formulaCells }
          };
        }

        return {
          type: 'other',
          confidence: 0.5,
          details: { textRatio: stats.textCells / nonEmptyCells }
        };
      }

      _getCellType(value) {
        if (value === null || value === undefined || value === '') return 'empty';
        if (value instanceof Date) return 'date';
        if (typeof value === 'number') return 'number';
        if (typeof value === 'string') {
          if(/^\\d{4}[\\-\\/]\\d{2}[\\-\\/]\\d{2}/.test(value)) return 'date';
          return 'text';
        }
        if (typeof value === 'object') {
          if (value.text || value.result !== undefined) {
            return this._getCellType(value.text || value.result);
          }
        }
        return 'text';
      }

      generateReport() {
        const analysis = this.analyze();
        
        let report = '=== 工作表结构分析报告 ===\\n\\n';
        report += '表头行: 第 ' + analysis.headerRow + ' 行\\n';
        report += '空白行: ' + (analysis.blankRows.length > 0 ? analysis.blankRows.join(', ') : '无') + '\\n';
        report += '数据起始行: 第 ' + analysis.dataStartRow + ' 行\\n';
        report += '数据结束行: 第 ' + analysis.dataEndRow + ' 行\\n';
        report += '汇总行: 第 ' + analysis.summaryRow + ' 行\\n\\n';
        
        report += '详细结构:\\n';
        analysis.structure.forEach(item => {
          report += '  第 ' + item.rowNum + ' 行: ' + item.type + ' (置信度: ' + item.confidence + ')\\n';
        });

        return report;
      }
    }
    return { SmartSheetAnalyzer };
  `;
  
  const fn = new Function(code + '; return { SmartSheetAnalyzer };');
  return fn();
};

// 加载 autoAnalyzeSheet
const loadAutoAnalyzer = async () => {
  const code = `
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
          }
          else if (type === 'number') number++;
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
          if(/^\\d{4}[\\-\\/]\\d{2}[\\-\\/]\\d{2}/.test(value)) return 'date';
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
    return { autoAnalyzeSheet };
  `;
  
  const fn = new Function(code + '; return { autoAnalyzeSheet };');
  return fn();
};

describe('集成测试 - 分析器一致性', () => {
  let SmartSheetAnalyzer;
  let autoAnalyzeSheet;

  beforeEach(async () => {
    const module1 = await loadSmartSheetAnalyzer();
    SmartSheetAnalyzer = module1.SmartSheetAnalyzer;
    
    const module2 = await loadAutoAnalyzer();
    autoAnalyzeSheet = module2.autoAnalyzeSheet;
  });

  describe('两种实现应该对相同输入产生一致结果', () => {
    it('标准销售数据表', () => {
      const ws1 = TestTemplates.salesData();
      const ws2 = TestTemplates.salesData();

      const analyzer = new SmartSheetAnalyzer(ws1);
      const result1 = analyzer.analyze();
      const result2 = autoAnalyzeSheet(ws2);

      expect(result1.headerRow).toBe(result2.headerRow);
      expect(result1.dataStartRow).toBe(result2.dataStartRow);
      expect(result1.blankRows).toEqual(result2.blankRows);
    });

    it('带空白行的复杂表', () => {
      const ws1 = TestTemplates.complexWithBlanks();
      const ws2 = TestTemplates.complexWithBlanks();

      const analyzer = new SmartSheetAnalyzer(ws1);
      const result1 = analyzer.analyze();
      const result2 = autoAnalyzeSheet(ws2);

      expect(result1.headerRow).toBe(result2.headerRow);
    });

    it('中文关键词表', () => {
      const ws1 = TestTemplates.chineseKeywords();
      const ws2 = TestTemplates.chineseKeywords();

      const analyzer = new SmartSheetAnalyzer(ws1);
      const result1 = analyzer.analyze();
      const result2 = autoAnalyzeSheet(ws2);

      expect(result1.headerRow).toBe(result2.headerRow);
      expect(result1.summaryRow).toBe(result2.summaryRow);
    });

    it('多行表头候选', () => {
      const ws1 = TestTemplates.multipleHeaderCandidates();
      const ws2 = TestTemplates.multipleHeaderCandidates();

      const analyzer = new SmartSheetAnalyzer(ws1);
      const result1 = analyzer.analyze();
      const result2 = autoAnalyzeSheet(ws2);

      expect(result1.headerRow).toBe(result2.headerRow);
    });
  });

  describe('边界情况处理', () => {
    it('空工作表', () => {
      const ws1 = TestTemplates.emptySheet();
      const ws2 = TestTemplates.emptySheet();

      const analyzer = new SmartSheetAnalyzer(ws1);
      const result1 = analyzer.analyze();
      const result2 = autoAnalyzeSheet(ws2);

      // SmartSheetAnalyzer 返回 null，autoAnalyzeSheet 默认返回 1
      expect(result1.headerRow).toBeNull();
      expect(result2.headerRow).toBe(1);
    });

    it('只有表头', () => {
      const ws1 = TestTemplates.headerOnly();
      const ws2 = TestTemplates.headerOnly();

      const analyzer = new SmartSheetAnalyzer(ws1);
      const result1 = analyzer.analyze();
      const result2 = autoAnalyzeSheet(ws2);

      expect(result1.headerRow).toBe(result2.headerRow);
    });
  });
});

describe('集成测试 - 完整工作流', () => {
  let SmartSheetAnalyzer;

  beforeEach(async () => {
    const module = await loadSmartSheetAnalyzer();
    SmartSheetAnalyzer = module.SmartSheetAnalyzer;
  });

  it('应该生成有效的分析报告', () => {
    const ws = TestTemplates.salesData();
    const analyzer = new SmartSheetAnalyzer(ws);
    const report = analyzer.generateReport();

    expect(report).toContain('工作表结构分析报告');
    expect(report).toContain('表头行');
    expect(report).toContain('数据起始行');
    expect(report).toContain('数据结束行');
    expect(report).toContain('汇总行');
    expect(report).toContain('详细结构');
  });

  it('分析报告应该包含所有行类型', () => {
    const ws = TestTemplates.salesData();
    const analyzer = new SmartSheetAnalyzer(ws);
    const report = analyzer.generateReport();

    expect(report).toContain('blank');
    expect(report).toContain('data');
    expect(report).toContain('summary');
  });

  it('多次分析应该返回相同结果', () => {
    const ws = TestTemplates.salesData();
    const analyzer = new SmartSheetAnalyzer(ws);

    const result1 = analyzer.analyze();
    const result2 = analyzer.analyze();

    expect(result1).toEqual(result2);
  });
});

describe('集成测试 - 复杂场景', () => {
  let SmartSheetAnalyzer;
  let autoAnalyzeSheet;

  beforeEach(async () => {
    const module1 = await loadSmartSheetAnalyzer();
    SmartSheetAnalyzer = module1.SmartSheetAnalyzer;
    
    const module2 = await loadAutoAnalyzer();
    autoAnalyzeSheet = module2.autoAnalyzeSheet;
  });

  it('应该处理带公式的工作表', () => {
    const ws = TestTemplates.withFormulas();
    const analyzer = new SmartSheetAnalyzer(ws);
    const result = analyzer.analyze();

    expect(result.headerRow).toBe(1);
    // 第二行有SUM公式，应该被识别为汇总行或数据行
    expect(result.structure.length).toBeGreaterThan(0);
  });

  it('应该处理带日期的工作表', () => {
    const ws = TestTemplates.withDates();
    const analyzer = new SmartSheetAnalyzer(ws);
    const result = analyzer.analyze();

    expect(result.headerRow).toBe(1);
    expect(result.dataStartRow).toBe(2);
  });

  it('应该处理富文本对象', () => {
    const ws = TestTemplates.withRichText();
    const analyzer = new SmartSheetAnalyzer(ws);
    const result = analyzer.analyze();

    expect(result.headerRow).toBe(1);
  });

  it('应该处理大量数据的工作表', () => {
    const rows = [['序号', '名称', '数值']];
    for (let i = 1; i <= 50; i++) {
      rows.push([i, `项目${i}`, i * 100]);
    }
    rows.push(['合计', '', 127500]);

    const ws1 = createMockWorksheet(rows);
    const ws2 = createMockWorksheet(rows);

    const analyzer = new SmartSheetAnalyzer(ws1);
    const result1 = analyzer.analyze();
    const result2 = autoAnalyzeSheet(ws2);

    expect(result1.headerRow).toBe(1);
    expect(result1.dataStartRow).toBe(2);
    expect(result1.summaryRow).toBe(52);
  });
});
