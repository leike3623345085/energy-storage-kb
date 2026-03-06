/**
 * ExcelJS Mock 工具 - 用于测试智能工作表分析器
 * 提供创建工作表、行、单元格 Mock 对象的工厂函数
 */

/**
 * 创建 Mock 单元格
 * @param {any} value - 单元格值
 * @param {Object} options - 额外选项
 * @returns {Object} Mock Cell 对象
 */
export function createMockCell(value, options = {}) {
  return {
    value,
    formula: options.formula || null,
    style: options.style || null,
    numFmt: options.numFmt || null,
    result: options.result || null,
    ...options
  };
}

/**
 * 创建 Mock 行
 * @param {number} rowNum - 行号
 * @param {Array} cellValues - 单元格值数组
 * @param {Object} options - 额外选项
 * @returns {Object} Mock Row 对象
 */
export function createMockRow(rowNum, cellValues = [], options = {}) {
  const cells = cellValues.map((val, idx) => {
    if (val && typeof val === 'object' && 'value' in val) {
      return { ...val, col: idx + 1 };
    }
    return createMockCell(val, { col: idx + 1 });
  });

  return {
    rowNum,
    height: options.height || 15,
    hidden: options.hidden || false,
    cells,
    
    /**
     * 遍历单元格（模拟 ExcelJS 的 eachCell）
     * @param {Object} options - 选项 { includeEmpty: boolean }
     * @param {Function} callback - 回调函数 (cell, colNumber) => void
     */
    eachCell(opts, callback) {
      if (typeof opts === 'function') {
        callback = opts;
        opts = {};
      }
      
      const maxCol = Math.max(cells.length, 10);
      for (let i = 1; i <= maxCol; i++) {
        const cell = cells[i - 1] || createMockCell(null, { col: i });
        if (!opts.includeEmpty && (cell.value === null || cell.value === undefined || cell.value === '')) {
          continue;
        }
        callback(cell, i);
      }
    },

    /**
     * 获取指定列的单元格
     * @param {number} col - 列号
     * @returns {Object} Mock Cell
     */
    getCell(col) {
      return cells[col - 1] || createMockCell(null, { col });
    },

    /**
     * 提交行更改（模拟）
     */
    commit() {
      // 模拟提交操作
    }
  };
}

/**
 * 创建 Mock 工作表
 * @param {Array} rowsData - 行数据数组，每项是单元格值数组
 * @param {Object} options - 额外选项
 * @returns {Object} Mock Worksheet 对象
 */
export function createMockWorksheet(rowsData = [], options = {}) {
  const rows = rowsData.map((cells, idx) => 
    createMockRow(idx + 1, cells, options.rowOptions)
  );

  return {
    rowCount: rows.length,
    columnCount: options.columnCount || 10,
    _merges: options.merges || {},
    rows,

    /**
     * 获取指定行
     * @param {number} rowNum - 行号
     * @returns {Object} Mock Row
     */
    getRow(rowNum) {
      return rows[rowNum - 1] || createMockRow(rowNum, []);
    },

    /**
     * 插入行
     * @param {number} startRow - 开始行号
     * @param {number} count - 插入数量
     * @param {Array} data - 插入的数据
     */
    spliceRows(startRow, count, ...data) {
      // 简化实现：仅更新 rowCount
      this.rowCount += data.length - count;
    },

    /**
     * 合并单元格
     */
    mergeCells(top, left, bottom, right) {
      const key = `${top}:${left}`;
      this._merges[key] = { top, left, bottom, right };
    },

    /**
     * 取消合并单元格
     */
    unMergeCells(key) {
      delete this._merges[key];
    },

    /**
     * 获取工作表（模拟）
     * @param {string} name - 工作表名称
     * @returns {Object} this
     */
    getWorksheet(name) {
      return this;
    }
  };
}

/**
 * 预定义的测试数据模板
 */
export const TestTemplates = {
  /**
   * 标准销售数据表
   */
  salesData() {
    return createMockWorksheet([
      ['序号', '产品名称', '数量', '单价', '金额'],  // 表头
      [1, '产品A', 10, 100, 1000],                    // 数据行
      [2, '产品B', 20, 50, 1000],
      [3, '产品C', 15, 80, 1200],
      ['', '', '', '', ''],                           // 空白行
      ['合计', '', '', '', 3200],                     // 汇总行
    ]);
  },

  /**
   * 带空白行的复杂表
   */
  complexWithBlanks() {
    return createMockWorksheet([
      ['', '', '', '', ''],                           // 空行
      ['姓名', '日期', '部门', '金额', '备注'],       // 表头
      ['', '', '', '', ''],                           // 空白行
      ['张三', '2024-01-01', '销售', 5000, ''],       // 数据
      ['李四', '2024-01-02', '技术', 6000, ''],
      ['', '', '', '', ''],                           // 空白行
      ['', '', '', '', ''],                           // 连续空白
      ['王五', '2024-01-03', '人事', 5500, ''],       // 数据继续
      ['合计', '', '', 16500, ''],                    // 汇总
    ]);
  },

  /**
   * 只有表头没有数据
   */
  headerOnly() {
    return createMockWorksheet([
      ['列1', '列2', '列3', '列4', '列5'],
    ]);
  },

  /**
   * 空工作表
   */
  emptySheet() {
    return createMockWorksheet([]);
  },

  /**
   * 大量数字（非表头）
   */
  mostlyNumbers() {
    return createMockWorksheet([
      [100, 200, 300, 400, 500],
      [1, 2, 3, 4, 5],
      ['名称', '数值1', '数值2', '数值3', '总计'],
      ['A', 10, 20, 30, 60],
    ]);
  },

  /**
   * 带公式的工作表
   */
  withFormulas() {
    return createMockWorksheet([
      ['项目', 'Q1', 'Q2', 'Q3', 'Q4'],
      ['收入', 
        { value: 1000, formula: 'SUM(B3:B10)' },
        { value: 1200, formula: 'SUM(C3:C10)' },
        { value: 1100, formula: 'SUM(D3:D10)' },
        { value: 1300, formula: 'SUM(E3:E10)' }
      ],
      ['支出', 500, 600, 550, 650],
      ['利润', 
        { value: 500, formula: 'B2-B3' },
        { value: 600, formula: 'C2-C3' },
        { value: 550, formula: 'D2-D3' },
        { value: 650, formula: 'E2-E3' }
      ],
    ].map((row, idx) => 
      row.map(cell => 
        typeof cell === 'object' && 'formula' in cell
          ? cell
          : cell
      )
    ));
  },

  /**
   * 带日期的工作表
   */
  withDates() {
    return createMockWorksheet([
      ['日期', '事件', '金额'],
      [new Date('2024-01-01'), '新年', 100],
      ['2024-02-14', '情人节', 200],
      ['2024/03/08', '妇女节', 150],
    ]);
  },

  /**
   * 富文本对象
   */
  withRichText() {
    return createMockWorksheet([
      ['标题', '内容'],
      [
        { text: '富文本标题', richText: [{ text: '富文本标题' }] },
        { result: 100, text: '100' }
      ],
      ['普通文本', 200],
    ]);
  },

  /**
   * 中文关键词测试
   */
  chineseKeywords() {
    return createMockWorksheet([
      ['序号', '姓名', '日期', '金额', '数量', '编号'],
      [1, '张三', '2024-01-01', 1000, 10, 'NO001'],
      [2, '李四', '2024-01-02', 2000, 20, 'NO002'],
      ['合计', '', '', 3000, 30, ''],
    ]);
  },

  /**
   * 多行表头候选
   */
  multipleHeaderCandidates() {
    return createMockWorksheet([
      ['报表标题', '', '', '', ''],                    // 标题行（长文本）
      ['', '', '', '', ''],                           // 空行
      ['ID', 'Name', 'Value', 'Date', 'Status'],      // 真正表头（短英文）
      [1, 'Item1', 100, '2024-01-01', 'Active'],
      [2, 'Item2', 200, '2024-01-02', 'Pending'],
    ]);
  }
};

/**
 * 创建自定义 Mock 工作表的辅助函数
 * @param {Function} setupFn - 设置函数，接收 worksheet 进行自定义
 * @returns {Object} Mock Worksheet
 */
export function createCustomWorksheet(setupFn) {
  const ws = createMockWorksheet([]);
  if (setupFn) setupFn(ws);
  return ws;
}
