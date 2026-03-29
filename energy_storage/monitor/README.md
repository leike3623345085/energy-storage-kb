# 任务执行实时监控面板

实时可视化展示 OpenClaw 定时任务的执行状态和趋势。

## 功能特性

| 功能 | 说明 |
|------|------|
| **实时数据推送** | WebSocket 每5秒自动刷新 |
| **统计概览** | 总任务数、今日成功/失败/总数 |
| **24小时趋势** | 按小时展示任务执行趋势 |
| **任务列表** | 显示所有任务及最近状态 |
| **错误监控** | 最近失败的错误列表 |
| **成功率趋势** | 7天成功率柱状图 |

## 技术栈

- **后端**: Flask + Flask-SocketIO
- **前端**: HTML5 + Chart.js
- **数据库**: SQLite
- **实时通信**: WebSocket

## 快速启动

```bash
cd /root/.openclaw/workspace/energy_storage
chmod +x monitor/start_dashboard.sh
./monitor/start_dashboard.sh
```

然后访问: http://localhost:5000

## 手动启动

```bash
# 1. 安装依赖
pip install flask flask-socketio

# 2. 启动服务
cd /root/.openclaw/workspace/energy_storage
python3 monitor/dashboard_server.py
```

## 文件结构

```
monitor/
├── collector.py           # 数据收集器
├── dashboard_server.py    # Web 服务端
├── start_dashboard.sh     # 启动脚本
├── templates/
│   └── dashboard.html     # 监控面板页面
└── README.md
```

## API 接口

| 接口 | 说明 |
|------|------|
| `GET /` | 监控面板首页 |
| `GET /api/dashboard` | 仪表盘数据 |
| `GET /api/tasks` | 任务列表 |
| `GET /api/executions/<task_id>` | 任务执行历史 |
| `GET /api/stats` | 统计图表数据 |

## WebSocket 事件

| 事件 | 方向 | 说明 |
|------|------|------|
| `connect` | C→S | 客户端连接 |
| `dashboard_update` | S→C | 数据更新推送 |
| `request_update` | C→S | 请求立即更新 |

## 数据表结构

### tasks
- id: 任务ID
- name: 任务名称
- schedule: 调度配置
- enabled: 是否启用

### task_executions
- task_id: 任务ID
- task_name: 任务名称
- started_at: 开始时间
- completed_at: 完成时间
- duration_ms: 执行时长
- status: 状态 (success/error/timeout/running)
- error_message: 错误信息

### task_stats
- task_id: 任务ID
- total_runs: 总运行次数
- success_runs: 成功次数
- error_runs: 失败次数
- last_run_at: 最后执行时间
- last_status: 最后状态
- consecutive_errors: 连续错误次数

## 扩展建议

1. **添加告警功能**: 连续失败时发送邮件/企微通知
2. **任务详情页**: 点击任务查看详细执行日志
3. **性能优化**: 数据量大时使用 Redis 缓存
4. **移动端适配**: 优化手机端显示
5. **历史回放**: 支持查看任意时间点的状态
