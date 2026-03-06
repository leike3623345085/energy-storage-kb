# WASM数据分析平台 - 优化验证清单

## 文件信息
- **优化文件**: WASM数据分析.html
- **备份建议**: 在测试前备份原始文件
- **浏览器要求**: Chrome 80+, Firefox 75+, Safari 13+, Edge 80+

---

## 快速验证步骤

### 1. 页面加载检查
打开浏览器开发者工具 (F12)，查看 Console：

```
✅ 期望输出:
ExcelJS 版本已加载 - 完全免费，支持格式保留
Web Worker 初始化成功

⚠️ 如果看到:
Web Worker 初始化失败: ...
这是正常的，某些浏览器可能限制 Worker
```

### 2. 正则表达式优化验证
在 Console 运行：

```javascript
// 检查常量是否定义
console.log('DATE_PATTERNS:', typeof DATE_PATTERNS);
console.log('STRING_PATTERNS:', typeof STRING_PATTERNS);
console.log('FIELD_KEYWORDS:', FIELD_KEYWORDS.length);

// 期望输出:
// DATE_PATTERNS: object
// STRING_PATTERNS: object
// FIELD_KEYWORDS: 28 (或类似数字)
```

### 3. 虚拟滚动验证

**测试步骤**:
1. 上传一个包含 600+ 行数据的 Excel 文件
2. 执行数据关联查询
3. 检查结果区域是否显示："共 600 行数据（虚拟滚动模式）"

**验证方法**:
```javascript
// 在 Console 运行
const container = document.getElementById('join-table-container');
console.log('虚拟滚动内容:', container.querySelector('#virtual-scroll-content'));

// 期望: 如果数据量 > 500，应该存在 virtual-scroll-content 元素
```

### 4. 动态批次大小验证

**测试步骤**:
1. 上传不同大小的文件（1000行、10000行、50000行）
2. 执行查询时观察 Console 输出

**期望输出**:
```
动态批次大小: 200 (总行数: 10000)
动态批次大小: 1000 (总行数: 50000)
```

### 5. 内存清理验证

**测试步骤**:
1. 上传一个大文件（10000+ 行）
2. 执行查询
3. 点击"清除文件"按钮
4. 在 Console 运行：

```javascript
console.log('fuzzyIndexes 已清理:', Object.keys(fuzzyIndexes).length === 0);
console.log('s1MatchesGlobal 长度:', s1MatchesGlobal.length);
console.log('s2MatchesGlobal 长度:', s2MatchesGlobal.length);

// 期望: true, 0, 0
```

---

## 功能回归测试

### 数据关联功能
- [ ] 上传 Excel 文件
- [ ] 选择主数据表
- [ ] 添加关联条件（完全匹配）
- [ ] 添加关联条件（模糊匹配）
- [ ] 执行查询
- [ ] 选择输出列
- [ ] 导出结果（新建工作表）
- [ ] 导出结果（填充现有表）

### 字段映射功能
- [ ] 上传 Excel 文件
- [ ] 选择源表和目标表
- [ ] 自动匹配字段
- [ ] 执行字段映射
- [ ] 下载结果文件

### 业绩计算功能
- [ ] 上传业绩数据
- [ ] 识别协同标记（*）
- [ ] 配置单价和阶梯规则
- [ ] 执行计算
- [ ] 导出计算结果

---

## 性能对比测试

### 测试数据准备
创建一个测试 Excel 文件，包含：
- 表头行（第1行）
- 数据行（10000行）
- 列：姓名、日期、金额、备注

### 测试步骤

1. **打开浏览器开发者工具**
   - 切换到 Performance 标签
   - 点击录制按钮

2. **执行测试流程**
   - 上传文件
   - 选择主表
   - 添加一个关联条件
   - 点击"执行查询"
   - 等待完成

3. **停止录制并分析**
   - 查看总执行时间
   - 检查是否有长任务（Long Tasks）
   - 查看内存使用曲线

### 预期改进

| 指标 | 优化前 | 优化后 | 改进 |
|------|--------|--------|------|
| 10000行渲染时间 | ~2s | ~500ms | 75% ↓ |
| 内存峰值 | ~150MB | ~80MB | 45% ↓ |
| UI 卡顿 | 明显 | 轻微 | 显著改善 |

---

## 常见问题排查

### 问题1: 虚拟滚动不工作
**症状**: 大数据量时仍然卡顿
**排查**:
```javascript
// 检查阈值设置
console.log(VIRTUAL_SCROLL_CONFIG.threshold);

// 检查数据量
console.log(matchedData.length);

// 检查容器高度
console.log(document.getElementById('join-table-container').clientHeight);
```

### 问题2: Web Worker 初始化失败
**症状**: Console 显示 "Web Worker 初始化失败"
**原因**:
- 浏览器不支持 Worker
- CSP (Content Security Policy) 限制
- 文件协议 (file://) 访问

**解决**:
- 使用 HTTP 服务器访问（如 `npx serve`）
- 检查浏览器控制台是否有 CSP 错误

### 问题3: 日期格式解析错误
**症状**: 日期显示为 "Invalid Date" 或格式错误
**排查**:
```javascript
// 测试日期解析
const testDates = [
    '2021-04-02',
    '2021/04/02',
    '44561',  // Excel 序列号
    'Fri Apr 02 2021 08:00:00 GMT+0800'
];

testDates.forEach(d => {
    console.log(d, '->', formatDateValue(d));
});
```

---

## 回滚方案

如果发现严重问题，需要回滚到原始版本：

1. 如果你有备份文件，直接替换
2. 如果没有备份，可以手动删除以下新增代码：
   - `VIRTUAL_SCROLL_CONFIG` 和相关函数
   - `calculateBatchSize` 函数
   - `MATCHER_WORKER_CODE` 和相关函数
   - 保留 `DATE_PATTERNS` 和 `STRING_PATTERNS`（零风险）

---

## 联系支持

如果遇到无法解决的问题：
1. 记录浏览器版本和操作系统
2. 导出 Console 错误日志
3. 提供测试数据文件（可脱敏）
4. 描述复现步骤

---

验证完成时间: ___________
验证人: ___________
结果: ☐ 通过  ☐ 部分通过  ☐ 未通过
