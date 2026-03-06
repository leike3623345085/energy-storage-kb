# 智能工作表分析器 - 测试计划与策略

## 1. 项目概述

本项目包含多个 JavaScript 文件，用于智能分析 Excel 工作表结构：
- `smart-sheet-analyzer.js` - SmartSheetAnalyzer 类（完整面向对象实现）
- `analyzer_code.js` - autoAnalyzeSheet 函数（函数式实现）
- `auto-analyzer-integration.js` - 集成到 exportToExisting 的版本
- `patch-auto-analyzer.js` - 补丁版本

## 2. 测试策略

### 2.1 测试类型

| 类型 | 说明 | 优先级 |
|------|------|--------|
| 单元测试 | 测试单个函数/方法的独立功能 | 高 |
| 集成测试 | 测试多个组件协同工作 | 中 |
| 边界测试 | 测试极端输入和异常情况 | 高 |
| 模拟测试 | 使用 Mock 对象模拟 ExcelJS 工作表 | 高 |

### 2.2 测试覆盖点

#### SmartSheetAnalyzer 类
- [x] 构造函数初始化
- [x] analyze() 主分析方法
- [x] _findHeaderRow() 表头识别
- [x] _scoreAsHeader() 表头评分
- [x] _analyzeBelowHeader() 下方行分析
- [x] _classifyRow() 行分类
- [x] _getCellType() 单元格类型判断
- [x] generateReport() 报告生成

#### autoAnalyzeSheet 函数
- [x] 整体分析流程
- [x] findHeaderRow 内部函数
- [x] scoreAsHeader 评分逻辑
- [x] analyzeBelowHeader 分析逻辑
- [x] classifyRow 分类逻辑
- [x] getCellType 类型判断

### 2.3 边界情况

- 空工作表
- 只有表头没有数据
- 大量空白行
- 复杂公式单元格
- 富文本单元格
- 日期字符串格式
- 特殊字符和中文

## 3. Mock 设计

由于代码依赖 ExcelJS 的 worksheet 对象，需要创建 Mock：

```javascript
// Mock Worksheet 结构
{
  rowCount: number,
  getRow: (rowNum) => MockRow,
  columnCount: number,
  _merges: object
}

// Mock Row 结构
{
  eachCell: (options, callback) => void,
  getCell: (col) => MockCell,
  height: number,
  hidden: boolean,
  commit: () => void
}

// Mock Cell 结构
{
  value: any,
  formula: string,
  style: object,
  numFmt: string,
  result: any
}
```

## 4. 测试文件结构

```
tests/
├── package.json          # 测试项目配置
├── vitest.config.js      # Vitest 配置
├── TEST_PLAN.md          # 本测试计划
├── RUN_TESTS.md          # 测试运行说明
├── mocks/
│   └── exceljs.mock.js   # ExcelJS Mock 工具
├── unit/
│   ├── smart-sheet-analyzer.test.js      # SmartSheetAnalyzer 单元测试
│   ├── analyzer-code.test.js             # autoAnalyzeSheet 单元测试
│   └── cell-type.test.js                 # 单元格类型判断专项测试
├── integration/
│   └── analyzer-integration.test.js      # 集成测试
└── coverage/
    └── (generated)       # 覆盖率报告
```

## 5. 预期覆盖率目标

| 指标 | 目标 |
|------|------|
| 语句覆盖率 | ≥ 90% |
| 分支覆盖率 | ≥ 85% |
| 函数覆盖率 | ≥ 95% |
| 行覆盖率 | ≥ 90% |
