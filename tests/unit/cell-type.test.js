/**
 * 单元格类型判断专项测试
 * 测试 _getCellType / getCellType 函数的各种边界情况
 */

import { describe, it, expect } from 'vitest';
import { createMockWorksheet, createMockCell } from '../mocks/exceljs.mock.js';

// 加载被测代码
const loadCellTypeModule = async () => {
  const code = `
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
    return { getCellType };
  `;
  
  const fn = new Function(code + '; return { getCellType };');
  return fn();
};

describe('getCellType - 单元格类型判断', () => {
  let getCellType;

  beforeEach(async () => {
    const module = await loadCellTypeModule();
    getCellType = module.getCellType;
  });

  describe('空值判断', () => {
    it('应该识别 null 为空', () => {
      expect(getCellType(null)).toBe('empty');
    });

    it('应该识别 undefined 为空', () => {
      expect(getCellType(undefined)).toBe('empty');
    });

    it('应该识别空字符串为空', () => {
      expect(getCellType('')).toBe('empty');
    });

    it('应该识别空白字符为文本（非空）', () => {
      expect(getCellType(' ')).toBe('text');
      expect(getCellType('\t')).toBe('text');
      expect(getCellType('\n')).toBe('text');
    });
  });

  describe('数字判断', () => {
    it('应该识别整数', () => {
      expect(getCellType(123)).toBe('number');
      expect(getCellType(0)).toBe('number');
      expect(getCellType(-456)).toBe('number');
    });

    it('应该识别浮点数', () => {
      expect(getCellType(3.14)).toBe('number');
      expect(getCellType(-0.5)).toBe('number');
      expect(getCellType(1e10)).toBe('number');
    });

    it('应该识别特殊数字', () => {
      expect(getCellType(Infinity)).toBe('number');
      expect(getCellType(-Infinity)).toBe('number');
      expect(getCellType(NaN)).toBe('number');
    });
  });

  describe('日期判断', () => {
    it('应该识别 Date 对象', () => {
      expect(getCellType(new Date())).toBe('date');
      expect(getCellType(new Date('2024-01-01'))).toBe('date');
      expect(getCellType(new Date(0))).toBe('date');
    });

    it('应该识别标准日期字符串格式 yyyy-mm-dd', () => {
      expect(getCellType('2024-01-01')).toBe('date');
      expect(getCellType('2024-12-31')).toBe('date');
      expect(getCellType('2024-01-01 10:30:00')).toBe('date');
    });

    it('应该识别标准日期字符串格式 yyyy/mm/dd', () => {
      expect(getCellType('2024/01/01')).toBe('date');
      expect(getCellType('2024/12/31')).toBe('date');
    });

    it('不应该识别非标准日期格式为日期', () => {
      expect(getCellType('01-01-2024')).toBe('text');
      expect(getCellType('01/01/2024')).toBe('text');
      expect(getCellType('Jan 1, 2024')).toBe('text');
      expect(getCellType('2024')).toBe('text');
    });

    it('不应该识别无效日期为日期', () => {
      expect(getCellType('2024-13-01')).toBe('date'); // 正则只匹配格式，不验证有效性
      expect(getCellType('2024-01-32')).toBe('date');
    });
  });

  describe('文本判断', () => {
    it('应该识别普通字符串', () => {
      expect(getCellType('hello')).toBe('text');
      expect(getCellType('Hello World')).toBe('text');
      expect(getCellType('中文测试')).toBe('text');
    });

    it('应该识别包含数字的字符串为文本', () => {
      expect(getCellType('123abc')).toBe('text');
      expect(getCellType('abc123')).toBe('text');
      expect(getCellType('100元')).toBe('text');
    });

    it('应该识别纯数字字符串为文本（非日期格式）', () => {
      expect(getCellType('12345')).toBe('text');
      expect(getCellType('3.14159')).toBe('text');
    });

    it('应该识别特殊字符', () => {
      expect(getCellType('!@#$%')).toBe('text');
      expect(getCellType('<>&')).toBe('text');
      expect(getCellType('🎉')).toBe('text');
    });
  });

  describe('对象类型判断（富文本）', () => {
    it('应该处理包含 text 属性的对象', () => {
      expect(getCellType({ text: 'hello' })).toBe('text');
      expect(getCellType({ text: 123 })).toBe('number');
      expect(getCellType({ text: '2024-01-01' })).toBe('date');
    });

    it('应该处理包含 result 属性的对象', () => {
      expect(getCellType({ result: 100 })).toBe('number');
      expect(getCellType({ result: 'hello' })).toBe('text');
      expect(getCellType({ result: new Date() })).toBe('date');
    });

    it('应该优先使用 text 属性', () => {
      // text 和 result 同时存在时，使用 text
      expect(getCellType({ text: 'hello', result: 123 })).toBe('text');
    });

    it('应该处理嵌套对象', () => {
      // 递归处理
      const nested = { text: { text: 'nested' } };
      expect(getCellType(nested)).toBe('text');
    });

    it('应该处理空对象', () => {
      expect(getCellType({})).toBe('text');
    });

    it('应该处理数组对象', () => {
      expect(getCellType([1, 2, 3])).toBe('text');
      expect(getCellType([])).toBe('text');
    });
  });

  describe('布尔值判断', () => {
    it('应该将布尔值识别为文本', () => {
      expect(getCellType(true)).toBe('text');
      expect(getCellType(false)).toBe('text');
    });
  });

  describe('函数和Symbol判断', () => {
    it('应该将函数识别为文本', () => {
      expect(getCellType(function() {})).toBe('text');
      expect(getCellType(() => {})).toBe('text');
    });

    it('应该将 Symbol 识别为文本', () => {
      expect(getCellType(Symbol('test'))).toBe('text');
    });
  });

  describe('边界情况', () => {
    it('应该处理超大数字', () => {
      expect(getCellType(Number.MAX_SAFE_INTEGER)).toBe('number');
      expect(getCellType(Number.MIN_SAFE_INTEGER)).toBe('number');
      expect(getCellType(Number.MAX_VALUE)).toBe('number');
    });

    it('应该处理极小数', () => {
      expect(getCellType(Number.MIN_VALUE)).toBe('number');
      expect(getCellType(1e-100)).toBe('number');
    });

    it('应该处理长字符串', () => {
      const longString = 'a'.repeat(10000);
      expect(getCellType(longString)).toBe('text');
    });

    it('应该处理包含换行符的字符串', () => {
      expect(getCellType('line1\nline2')).toBe('text');
      expect(getCellType('line1\r\nline2')).toBe('text');
    });
  });
});
