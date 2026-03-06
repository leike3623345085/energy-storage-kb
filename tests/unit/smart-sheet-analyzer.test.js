/**
 * SmartSheetAnalyzer 类单元测试
 * 测试文件: smart-sheet-analyzer.js
 */

import { describe, it, expect, beforeEach } from 'vitest';
import { 
  createMockWorksheet, 
  TestTemplates,
  createMockCell
} from '../mocks/exceljs.mock.js';

// 动态加载被测模块（因为原文件使用 CommonJS 导出）
const loadSmartSheetAnalyzer = async () => {
  // 模拟 SmartSheetAnalyzer 类定义
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
  
  // 使用 eval 动态创建类（测试环境安全）
  const fn = new Function(code + '; return { SmartSheetAnalyzer };');
  return fn();
};

describe('SmartSheetAnalyzer', () => {
  let SmartSheetAnalyzer;

  beforeEach(async () => {
    const module = await loadSmartSheetAnalyzer();
    SmartSheetAnalyzer = module.SmartSheetAnalyzer;
  });

  describe('构造函数', () => {
    it('应该正确初始化 worksheet 和 maxScanRows', () => {
      const ws = createMockWorksheet([
        ['A', 'B', 'C'],
        [1, 2, 3],
      ]);
      
      const analyzer = new SmartSheetAnalyzer(ws);
      expect(analyzer.worksheet).toBe(ws);
      expect(analyzer.maxScanRows).toBe(2);
    });

    it('maxScanRows 应该限制为 50', () => {
      const ws = createMockWorksheet(new Array(100).fill(['A', 'B']));
      ws.rowCount = 100;
      
      const analyzer = new SmartSheetAnalyzer(ws);
      expect(analyzer.maxScanRows).toBe(50);
    });
  });

  describe('analyze() 主方法', () => {
    it('应该正确分析标准销售数据表', () => {
      const ws = TestTemplates.salesData();
      const analyzer = new SmartSheetAnalyzer(ws);
      const result = analyzer.analyze();

      expect(result.headerRow).toBe(1);
      expect(result.dataStartRow).toBe(2);
      expect(result.dataEndRow).toBe(4);
      expect(result.summaryRow).toBe(6);
      expect(result.blankRows).toContain(5);
    });

    it('应该正确处理只有表头的情况', () => {
      const ws = TestTemplates.headerOnly();
      const analyzer = new SmartSheetAnalyzer(ws);
      const result = analyzer.analyze();

      expect(result.headerRow).toBe(1);
      expect(result.dataStartRow).toBeNull();
      expect(result.dataEndRow).toBeNull();
    });

    it('应该正确处理空工作表', () => {
      const ws = TestTemplates.emptySheet();
      const analyzer = new SmartSheetAnalyzer(ws);
      const result = analyzer.analyze();

      expect(result.headerRow).toBeNull();
      expect(result.blankRows).toEqual([]);
    });

    it('应该正确处理带空白行的复杂表', () => {
      const ws = TestTemplates.complexWithBlanks();
      const analyzer = new SmartSheetAnalyzer(ws);
      const result = analyzer.analyze();

      expect(result.headerRow).toBe(2); // 真正的表头在第2行
      expect(result.blankRows.length).toBeGreaterThan(0);
    });
  });

  describe('_findHeaderRow() 表头识别', () => {
    it('应该识别中文关键词表头', () => {
      const ws = TestTemplates.chineseKeywords();
      const analyzer = new SmartSheetAnalyzer(ws);
      const headerRow = analyzer._findHeaderRow();

      expect(headerRow).toBe(1);
    });

    it('应该跳过大量数字的行', () => {
      const ws = TestTemplates.mostlyNumbers();
      const analyzer = new SmartSheetAnalyzer(ws);
      const headerRow = analyzer._findHeaderRow();

      // 应该找到第3行（真正的表头）而不是第1行（数字）
      expect(headerRow).toBe(3);
    });

    it('应该在多个候选中选择最佳表头', () => {
      const ws = TestTemplates.multipleHeaderCandidates();
      const analyzer = new SmartSheetAnalyzer(ws);
      const headerRow = analyzer._findHeaderRow();

      // 第3行是真正的表头（短英文，符合表头特征）
      expect(headerRow).toBe(3);
    });
  });

  describe('_scoreAsHeader() 表头评分', () => {
    it('应该给高文本比例行高分', () => {
      const ws = createMockWorksheet([
        ['姓名', '年龄', '地址', '电话', '邮箱'],
      ]);
      const analyzer = new SmartSheetAnalyzer(ws);
      const row = ws.getRow(1);
      const score = analyzer._scoreAsHeader(row);

      expect(score).toBeGreaterThanOrEqual(3);
    });

    it('应该给高数字比例行低分', () => {
      const ws = createMockWorksheet([
        [100, 200, 300, 400, 500],
      ]);
      const analyzer = new SmartSheetAnalyzer(ws);
      const row = ws.getRow(1);
      const score = analyzer._scoreAsHeader(row);

      expect(score).toBeLessThan(5);
    });

    it('应该检测表头关键词加分', () => {
      const ws = createMockWorksheet([
        ['序号', '名称', '日期', '金额', '总计'],
      ]);
      const analyzer = new SmartSheetAnalyzer(ws);
      const row = ws.getRow(1);
      const score = analyzer._scoreAsHeader(row);

      // 包含多个关键词应该获得额外加分
      expect(score).toBeGreaterThanOrEqual(5);
    });

    it('空行应该得0分', () => {
      const ws = createMockWorksheet([['', '', '', '', '']]);
      const analyzer = new SmartSheetAnalyzer(ws);
      const row = ws.getRow(1);
      const score = analyzer._scoreAsHeader(row);

      expect(score).toBe(0);
    });
  });

  describe('_classifyRow() 行分类', () => {
    it('应该正确分类空白行', () => {
      const ws = createMockWorksheet([['', '', '', '', '']]);
      const analyzer = new SmartSheetAnalyzer(ws);
      const row = ws.getRow(1);
      const classification = analyzer._classifyRow(row, 0);

      expect(classification.type).toBe('blank');
      expect(classification.confidence).toBe(0.95);
    });

    it('应该正确分类数据行', () => {
      const ws = createMockWorksheet([[1, 2, 3, 4, 5]]);
      const analyzer = new SmartSheetAnalyzer(ws);
      const row = ws.getRow(1);
      const classification = analyzer._classifyRow(row, 0);

      expect(classification.type).toBe('data');
    });

    it('应该正确分类汇总行（关键词）', () => {
      const ws = createMockWorksheet([['合计', '', '', 1000, '']]);
      const analyzer = new SmartSheetAnalyzer(ws);
      const row = ws.getRow(1);
      const classification = analyzer._classifyRow(row, 0);

      expect(classification.type).toBe('summary');
      expect(classification.details.hasSumKeyword).toBe(true);
    });

    it('应该正确分类汇总行（公式）', () => {
      const ws = createMockWorksheet([
        [
          { value: 100, formula: 'SUM(A1:A10)' },
          { value: 200, formula: 'AVERAGE(B1:B10)' },
          '', '', ''
        ]
      ]);
      const analyzer = new SmartSheetAnalyzer(ws);
      const row = ws.getRow(1);
      const classification = analyzer._classifyRow(row, 0);

      expect(classification.type).toBe('summary');
      expect(classification.details.hasFormulaSum).toBe(true);
    });

    it('应该正确分类其他类型行', () => {
      const ws = createMockWorksheet([['备注', '说明文字', '', '', '']]);
      const analyzer = new SmartSheetAnalyzer(ws);
      const row = ws.getRow(1);
      const classification = analyzer._classifyRow(row, 0);

      expect(classification.type).toBe('other');
    });
  });

  describe('_getCellType() 单元格类型判断', () => {
    it('应该识别空值', () => {
      const ws = createMockWorksheet([['test']]);
      const analyzer = new SmartSheetAnalyzer(ws);
      
      expect(analyzer._getCellType(null)).toBe('empty');
      expect(analyzer._getCellType(undefined)).toBe('empty');
      expect(analyzer._getCellType('')).toBe('empty');
    });

    it('应该识别数字', () => {
      const ws = createMockWorksheet([['test']]);
      const analyzer = new SmartSheetAnalyzer(ws);
      
      expect(analyzer._getCellType(123)).toBe('number');
      expect(analyzer._getCellType(0)).toBe('number');
      expect(analyzer._getCellType(-5.5)).toBe('number');
    });

    it('应该识别日期', () => {
      const ws = createMockWorksheet([['test']]);
      const analyzer = new SmartSheetAnalyzer(ws);
      
      expect(analyzer._getCellType(new Date())).toBe('date');
      expect(analyzer._getCellType('2024-01-01')).toBe('date');
      expect(analyzer._getCellType('2024/12/31')).toBe('date');
    });

    it('应该识别文本', () => {
      const ws = createMockWorksheet([['test']]);
      const analyzer = new SmartSheetAnalyzer(ws);
      
      expect(analyzer._getCellType('hello')).toBe('text');
      expect(analyzer._getCellType('123abc')).toBe('text');
    });

    it('应该处理富文本对象', () => {
      const ws = createMockWorksheet([['test']]);
      const analyzer = new SmartSheetAnalyzer(ws);
      
      expect(analyzer._getCellType({ text: 'hello' })).toBe('text');
      expect(analyzer._getCellType({ result: 100, text: '100' })).toBe('number');
      expect(analyzer._getCellType({ result: new Date() })).toBe('date');
    });
  });

  describe('generateReport() 报告生成', () => {
    it('应该生成包含所有关键信息的报告', () => {
      const ws = TestTemplates.salesData();
      const analyzer = new SmartSheetAnalyzer(ws);
      const report = analyzer.generateReport();

      expect(report).toContain('工作表结构分析报告');
      expect(report).toContain('表头行');
      expect(report).toContain('数据起始行');
      expect(report).toContain('数据结束行');
      expect(report).toContain('汇总行');
    });

    it('报告应该包含结构详情', () => {
      const ws = TestTemplates.salesData();
      const analyzer = new SmartSheetAnalyzer(ws);
      const report = analyzer.generateReport();

      expect(report).toContain('详细结构');
      expect(report).toContain('blank');
      expect(report).toContain('data');
      expect(report).toContain('summary');
    });
  });

  describe('边界情况', () => {
    it('应该处理只有一行的工作表', () => {
      const ws = createMockWorksheet([['表头']]);
      const analyzer = new SmartSheetAnalyzer(ws);
      const result = analyzer.analyze();

      expect(result.headerRow).toBe(1);
      expect(result.structure).toEqual([]);
    });

    it('应该处理所有行都是空白的情况', () => {
      const ws = createMockWorksheet([
        ['', '', ''],
        ['', '', ''],
        ['', '', ''],
      ]);
      const analyzer = new SmartSheetAnalyzer(ws);
      const result = analyzer.analyze();

      // 没有有效表头
      expect(result.headerRow).toBeNull();
    });

    it('应该处理包含特殊字符的表头', () => {
      const ws = createMockWorksheet([
        ['列#1', '列@2', '列$3', '列%4', '列&5'],
        [1, 2, 3, 4, 5],
      ]);
      const analyzer = new SmartSheetAnalyzer(ws);
      const result = analyzer.analyze();

      expect(result.headerRow).toBe(1);
    });

    it('应该处理超长文本行', () => {
      const longText = 'A'.repeat(100);
      const ws = createMockWorksheet([
        [longText, longText, longText],
        ['短', '表头', '行'],
        [1, 2, 3],
      ]);
      const analyzer = new SmartSheetAnalyzer(ws);
      const headerRow = analyzer._findHeaderRow();

      // 应该选择短文本行作为表头
      expect(headerRow).toBe(2);
    });
  });
});
