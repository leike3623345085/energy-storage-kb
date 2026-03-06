# 测试运行说明

## 项目概述

本项目为 JavaScript 智能工作表分析器编写了完整的测试套件，包括：

- **单元测试**: 测试各个独立函数和方法
- **集成测试**: 测试组件间的协同工作和一致性
- **边界测试**: 测试极端输入和异常情况

## 测试文件结构

```
tests/
├── package.json                    # 测试项目配置
├── vitest.config.js                # Vitest 配置
├── TEST_PLAN.md                    # 测试计划文档
├── RUN_TESTS.md                    # 本文件
├── mocks/
│   └── exceljs.mock.js             # ExcelJS Mock 工具
├── unit/
│   ├── smart-sheet-analyzer.test.js    # SmartSheetAnalyzer 类单元测试
│   ├── analyzer-code.test.js           # autoAnalyzeSheet 函数单元测试
│   └── cell-type.test.js               # 单元格类型判断专项测试
└── integration/
    └── analyzer-integration.test.js    # 集成测试
```

## 环境准备

### 1. 安装依赖

```bash
cd /root/.openclaw/workspace/tests
npm install
```

### 2. 验证安装

```bash
npm list vitest
```

## 运行测试

### 运行所有测试

```bash
npm test
```

或

```bash
npx vitest run
```

### 运行特定测试文件

```bash
# 只运行 SmartSheetAnalyzer 测试
npx vitest run unit/smart-sheet-analyzer.test.js

# 只运行 autoAnalyzeSheet 测试
npx vitest run unit/analyzer-code.test.js

# 只运行单元格类型测试
npx vitest run unit/cell-type.test.js

# 只运行集成测试
npx vitest run integration/analyzer-integration.test.js
```

### 监视模式（开发时使用）

```bash
npm run test:watch
```

### 生成覆盖率报告

```bash
npm run test:coverage
```

覆盖率报告将生成在 `tests/coverage/` 目录下：
- `coverage/text.txt` - 文本格式报告
- `coverage/html/index.html` - HTML 格式报告
- `coverage/coverage.json` - JSON 格式报告

### UI 模式

```bash
npm run test:ui
```

## 测试覆盖率目标

| 指标 | 目标 | 当前状态 |
|------|------|----------|
| 语句覆盖率 | ≥ 90% | 待运行测试后确定 |
| 分支覆盖率 | ≥ 85% | 待运行测试后确定 |
| 函数覆盖率 | ≥ 95% | 待运行测试后确定 |
| 行覆盖率 | ≥ 90% | 待运行测试后确定 |

## 测试覆盖的功能点

### SmartSheetAnalyzer 类

- ✅ 构造函数初始化
- ✅ analyze() 主分析方法
- ✅ _findHeaderRow() 表头识别
- ✅ _scoreAsHeader() 表头评分
- ✅ _analyzeBelowHeader() 下方行分析
- ✅ _classifyRow() 行分类
- ✅ _getCellType() 单元格类型判断
- ✅ generateReport() 报告生成

### autoAnalyzeSheet 函数

- ✅ 整体分析流程
- ✅ findHeaderRow 内部函数
- ✅ scoreAsHeader 评分逻辑
- ✅ analyzeBelowHeader 分析逻辑
- ✅ classifyRow 分类逻辑
- ✅ getCellType 类型判断

### 单元格类型判断

- ✅ 空值判断（null, undefined, ''）
- ✅ 数字判断（整数、浮点数、特殊数字）
- ✅ 日期判断（Date 对象、日期字符串）
- ✅ 文本判断（普通字符串、包含数字的字符串）
- ✅ 对象类型判断（富文本对象）
- ✅ 布尔值判断
- ✅ 函数和 Symbol 判断
- ✅ 边界情况（超大数字、极小数、长字符串）

### 边界情况

- ✅ 空工作表
- ✅ 只有表头没有数据
- ✅ 大量空白行
- ✅ 复杂公式单元格
- ✅ 富文本单元格
- ✅ 日期字符串格式
- ✅ 特殊字符和中文
- ✅ 超长文本行
- ✅ 连续空白行后的数据

## 常见问题

### 1. 测试运行失败

检查是否已安装依赖：
```bash
cd /root/.openclaw/workspace/tests
npm install
```

### 2. 覆盖率报告未生成

确保安装了 coverage 依赖：
```bash
npm install @vitest/coverage-v8
```

### 3. 特定测试文件失败

可以单独运行该文件查看详细错误：
```bash
npx vitest run --reporter=verbose unit/xxx.test.js
```

## 持续集成

建议在 CI/CD 流程中添加以下步骤：

```yaml
# 示例 GitHub Actions 配置
- name: Run Tests
  run: |
    cd tests
    npm ci
    npm test

- name: Generate Coverage
  run: |
    cd tests
    npm run test:coverage
```

## 扩展测试

如需添加新的测试：

1. 在 `unit/` 或 `integration/` 目录下创建 `.test.js` 文件
2. 从 `mocks/exceljs.mock.js` 导入 Mock 工具
3. 使用 `describe` 和 `it` 编写测试用例
4. 运行 `npm test` 验证

## 联系

如有问题，请参考：
- `TEST_PLAN.md` - 详细测试计划
- `mocks/exceljs.mock.js` - Mock 工具使用说明
