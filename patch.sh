#!/bin/bash

# 修改 WASM数据分析.html 添加自动识别功能

SRC="/root/openclaw/kimi/downloads/19ca3632-4352-8298-8000-00007c8c5e5d_WASM数据分析.html"
DST="/root/.openclaw/workspace/WASM数据分析_自动识别版.html"

# 复制原文件
cp "$SRC" "$DST"

echo "已创建修改版文件: $DST"
echo "文件大小: $(ls -lh $DST | awk '{print $5}')"
