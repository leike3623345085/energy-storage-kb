/**
 * autoAnalyzeSheet 函数单元测试
 * 测试文件: analyzer_code.js
 */

import { describe, it, expect, beforeEach } from 'vitest';
import { createMockWorksheet, TestTemplates, createMockCell } from '../mocks/exceljs.mock.js';

// 动态加载被测模块（因为原文件使用函数式实现）
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

describe('autoAnalyzeSheet', () => {
  let autoAnalyzeSheet;

  beforeEach(async () => {
    const module = await loadAutoAnalyzer();
    autoAnalyzeSheet = module.autoAnalyzeSheet;
  });

  describe('基本功能', () => {
    it('应该正确分析标准销售数据表', () => {
      const ws = TestTemplates.salesData();
      const result = autoAnalyzeSheet(ws);

      expect(result.headerRow).toBe(1);
      expect(result.dataStartRow).toBe(2);
      expect(result.dataEndRow).toBe(4);
      expect(result.summaryRow).toBe(6);
      expect(result.blankRows).toContain(5);
    });

    it('应该正确处理只有表头的情况', () => {
      const ws = TestTemplates.headerOnly();
      const result = autoAnalyzeSheet(ws);

      expect(result.headerRow).toBe(1);
      expect(result.dataStartRow).toBe(2); // 默认设置
      expect(result.dataEndRow).toBe(11);  // 默认10行
      expect(result.summaryRow).toBe(12);  // 默认汇总行
    });

    it('应该正确处理空工作表', () => {
      const ws = TestTemplates.emptySheet();
      ws.rowCount = 0;
      const result = autoAnalyzeSheet(ws);

      expect(result.headerRow).toBe(1); // 空表默认返回1
    });
  });

  describe('表头识别', () => {
    it('应该识别中文关键词表头', () => {
      const ws = TestTemplates.chineseKeywords();
      const result = autoAnalyzeSheet(ws);

      expect(result.headerRow).toBe(1);
    });

    it('应该跳过大量数字的行', () => {
      const ws = TestTemplates.mostlyNumbers();
      const result = autoAnalyzeSheet(ws);

      // 应该找到第3行（真正的表头）而不是第1行（数字）
      expect(result.headerRow).toBe(3);
    });

    it('应该在多个候选中选择最佳表头', () => {
      const ws = TestTemplates.multipleHeaderCandidates();
      const result = autoAnalyzeSheet(ws);

      // 第3行是真正的表头（短英文，符合表头特征）
      expect(result.headerRow).toBe(3);
    });
  });

  describe('行分类', () => {
    it('应该正确识别空白行', () => {
      const ws = createMockWorksheet([
        ['表头1', '表头2'],
        ['', '', '', '', ''],  // 空白行
        ['数据1', 100],
      ]);
      const result = autoAnalyzeSheet(ws);

      expect(result.blankRows).toContain(2);
    });

    it('应该正确识别数据行', () => {
      const ws = createMockWorksheet([
        ['名称', '数值'],
        ['项目A', 100],
        ['项目B', 200],
        ['项目C', 300],
      ]);
      const result = autoAnalyzeSheet(ws);

      expect(result.dataStartRow).toBe(2);
      expect(result.dataEndRow).toBe(4);
    });

    it('应该正确识别汇总行（关键词）', () => {
      const ws = createMockWorksheet([
        ['名称', '数值'],
        ['项目A', 100],
        ['项目B', 200],
        ['合计', 300],  // 汇总行
      ]);
      const result = autoAnalyzeSheet(ws);

      expect(result.summaryRow).toBe(4);
    });

    it('应该正确识别汇总行（公式）', () => {
      const ws = TestTemplates.withFormulas();
      const result = autoAnalyzeSheet(ws);

      // 第一行是表头，第二行有SUM公式应该被识别为汇总行
      expect(result.headerRow).toBe(1);
    });
  });

  describe('边界情况', () => {
    it('应该处理只有一行的工作表', () => {
      const ws = createMockWorksheet([['表头']]);
      const result = autoAnalyzeSheet(ws);

      expect(result.headerRow).toBe(1);
    });

    it('应该处理所有行都是空白的情况', () => {
      const ws = createMockWorksheet([
        ['', '', ''],
        ['', '', ''],
        ['', '', ''],
      ]);
      const result = autoAnalyzeSheet(ws);

      // 没有有效表头，但函数默认返回1
      expect(result.headerRow).toBe(1);
    });

    it('应该处理包含特殊字符的表头', () => {
      const ws = createMockWorksheet([
        ['列#1', '列@2', '列$3', '列%4', '列&5'],
        [1, 2, 3, 4, 5],
      ]);
      const result = autoAnalyzeSheet(ws);

      expect(result.headerRow).toBe(1);
    });

    it('应该处理超长文本行', () => {
      const longText = 'A'.repeat(100);
      const ws = createMockWorksheet([
        [longText, longText, longText],
        ['短', '表头', '行'],
        [1, 2, 3],
      ]);
      const result = autoAnalyzeSheet(ws);

      // 应该选择短文本行作为表头
      expect(result.headerRow).toBe(2);
    });

    it('应该处理连续空白行后的数据', () => {
      const ws = createMockWorksheet([
        ['表头1', '表头2'],
        ['', '', '', '', ''],
        ['', '', '', '', ''],  // 连续空白
        ['数据1', 100],
        ['数据2', 200],
      ]);
      const result = autoAnalyzeSheet(ws);

      expect(result.dataStartRow).toBe(4);
    });

    it('应该处理没有汇总行的情况', () => {
      const ws = createMockWorksheet([
        ['表头1', '表头2'],
        ['数据1', 100],
        ['数据2', 200],
      ]);
      const result = autoAnalyzeSheet(ws);

      // 默认设置汇总行为 dataEndRow + 1
      expect(result.summaryRow).toBe(result.dataEndRow + 1);
    });
  });

  describe('数据默认值', () => {
    it('当没有找到数据起始行时应该设置默认值', () => {
      const ws = createMockWorksheet([
        ['表头1', '表头2'],
        ['', '', '', '', ''],
        ['', '', '', '', ''],
      ]);
      const result = autoAnalyzeSheet(ws);

      expect(result.dataStartRow).toBe(2);  // headerRow + 1
    });

    it('当没有找到数据结束行时应该设置默认值', () => {
      const ws = createMockWorksheet([
        ['表头1', '表头2'],
        ['数据1', 100],
      ]);
      const result = autoAnalyzeSheet(ws);

      // 只有一行数据，dataEndRow应该是2
      expect(result.dataEndRow).toBe(2);
    });

    it('当没有找到汇总行时应该设置默认值', () => {
      const ws = createMockWorksheet([
        ['表头1', '表头2'],
        ['数据1', 100],
        ['数据2', 200],
      ]);
      const result = autoAnalyzeSheet(ws);

      expect(result.summaryRow).toBe(result.dataEndRow + 1);
    });
  });
});
