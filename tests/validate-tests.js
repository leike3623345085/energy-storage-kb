/**
 * 简单的测试验证脚本
 * 用于在没有完整测试环境时验证测试代码语法
 */

import { readFileSync } from 'fs';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const testFiles = [
  'unit/smart-sheet-analyzer.test.js',
  'unit/analyzer-code.test.js',
  'unit/cell-type.test.js',
  'integration/analyzer-integration.test.js',
  'mocks/exceljs.mock.js'
];

console.log('=== 测试文件语法验证 ===\n');

let allValid = true;

for (const file of testFiles) {
  const filePath = join(__dirname, file);
  try {
    const content = readFileSync(filePath, 'utf-8');
    
    // 基本语法检查
    // 1. 检查括号匹配
    const openParens = (content.match(/\(/g) || []).length;
    const closeParens = (content.match(/\)/g) || []).length;
    
    const openBraces = (content.match(/\{/g) || []).length;
    const closeBraces = (content.match(/\}/g) || []).length;
    
    const openBrackets = (content.match(/\[/g) || []).length;
    const closeBrackets = (content.match(/\]/g) || []).length;
    
    const issues = [];
    if (openParens !== closeParens) issues.push(`括号不匹配: ${openParens} vs ${closeParens}`);
    if (openBraces !== closeBraces) issues.push(`花括号不匹配: ${openBraces} vs ${closeBraces}`);
    if (openBrackets !== closeBrackets) issues.push(`方括号不匹配: ${openBrackets} vs ${closeBrackets}`);
    
    // 2. 检查基本结构 (mock 文件除外)
    if (!file.includes('mock')) {
      if (!content.includes('describe(')) issues.push('缺少 describe 定义');
      if (!content.includes('it(')) issues.push('缺少 it 定义');
    }
    
    // 3. 检查导入语句 (mock 文件除外)
    if (!file.includes('mock') && !content.includes('import')) issues.push('缺少 import 语句');
    
    if (issues.length === 0) {
      console.log(`✅ ${file} - 语法检查通过`);
      console.log(`   文件大小: ${content.length} 字符`);
      console.log(`   测试用例数: ${(content.match(/it\(/g) || []).length}`);
      console.log(`   测试套件数: ${(content.match(/describe\(/g) || []).length}`);
    } else {
      console.log(`❌ ${file} - 发现问题:`);
      issues.forEach(issue => console.log(`   - ${issue}`));
      allValid = false;
    }
    console.log('');
  } catch (error) {
    console.log(`❌ ${file} - 读取失败: ${error.message}\n`);
    allValid = false;
  }
}

console.log('=== 验证完成 ===');
if (allValid) {
  console.log('所有测试文件语法检查通过！');
  process.exit(0);
} else {
  console.log('部分文件存在问题，请检查。');
  process.exit(1);
}
