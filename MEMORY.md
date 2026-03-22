# MEMORY.md - 长期高价值记忆

> **跨项目通用记忆** —— 长期有效的偏好、决策、稳定规则
> 
> 参考：Memory Sync Protocol 六大控制面板

---

## 🎯 核心原则

### 执行准则
**遇到问题直接执行最优解决方案，事后通报结果** —— 不反复询问确认。

| 场景 | 行动 |
|------|------|
| 发现问题 | 立即分析 → 执行修复 → 通报结果 |
| 多种方案 | 选择最优直接执行，不逐一请示 |
| 需要确认 | 仅在涉及安全风险或重大变更时询问 |

### 执行准则细节
1. **先行动后汇报** — 修复完成再告知用户处理结果
2. **默认自主** — 常规运维问题自行决策执行
3. **记录留痕** — 所有操作自动保存到经验教训

---

## 🏗️ Harness Engineering 架构规范

### 核心原则
**所有工作流都必须复用 Harness Engineering 架构**

> "人类掌舵，智能体执行" — Humans steer. Agents execute.

### 新建工作流必须包含的组件
- **Guardrails** — 飞行前检查、输出验证
- **Feedback Loop** — 错误分类、自动修复、规则学习
- **Progressive Disclosure** — 分层上下文加载
- **Agent Runner** — 总控协调

### 禁止事项
- ❌ 直接调用 AI 生成而不经过 Guardrails 验证
- ❌ 忽略错误处理，不接入 Feedback Loop
- ❌ 一次性加载所有上下文，不使用 Progressive Disclosure
- ❌ 重复造轮子，不复用 harness/ 已有组件

### 工作流模板位置
- `energy_storage/harness/README.md` - 架构文档
- `energy_storage/harness/harness_config.yaml` - 配置参考

---

## 📝 记忆系统结构

遵循 Memory Sync Protocol，六大控制面板职责：

| 文件 | 职责 | 当前状态 |
|------|------|----------|
| **SOUL.md** | 人格、风格、原则、边界 | ✅ 活跃维护 |
| **USER.md** | 用户长期目标、沟通偏好 | ⚠️ 待填充 |
| **MEMORY.md** | 跨项目通用规则、决策 | ✅ 本文件 |
| **Daily** | 当日事件、决定、待办 | ✅ 自动维护 |
| **TOOLS.md** | 执行硬规则、路径、Skill路由 | ⚠️ 待完善 |
| **AGENTS.md** | 治理制度、风险确认策略 | ✅ 活跃维护 |

### 项目专属文档位置
- **储能系统**：`memory/system/energy-storage.md`
- **储能经验教训**：`memory/lessons/energy-storage.md`
- **储能更新记录**：`memory/system/energy-storage-updates.md`

---

## ⚙️ 定时任务通用规范

### Delivery 配置
- `mode: "announce"` 必须配合 `to: "main"` 使用
- 不需要推送通知的任务使用 `mode: "none"`

### 超时设置
- 简单脚本（读取文件、执行命令）：60 秒
- 网络请求任务：120-300 秒
- 复杂分析任务（需要 LLM 处理）：300-600 秒

### 任务设计原则
1. **脚本化优先** — 复杂逻辑写成 Python 脚本
2. **数据本地处理** — 避免在 Agent session 中传输大量数据
3. **幂等性** — 任务应能安全地重复执行
4. **错误隔离** — 使用 `sessionTarget: "isolated"`

---

## 📚 参考资源

- Memory Sync Protocol 详解：见今日头条分享（AI技术多元...）
- OpenClaw 文档：/usr/lib/node_modules/openclaw/docs
- 社区：https://discord.com/invite/clawd

---

_最后更新：2026-03-22 — 重构记忆系统，按六大控制面板拆分_
