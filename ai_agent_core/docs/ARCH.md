# AI Agent Core — Odoo 19

## Overview

Odoo 内的 Agent、聊天、知识检索和任务编排模块。核心模型为 `ai.coworker`、`ai.agent`、
`ai.coworker.session`、`ai.coworker.session.line`、`ai.provider`、`ai.model` 和 `ai.tool`。
平台实现细节仍以模块 README 为入口；19 分支的安装和验证见仓库根目录 `ODOO19.md`。

## Model Extensions & Schema

保留上游模型和业务表名称，未与亚博自研助手或 OCA AI 的表合并。
19 使用 `models.Constraint` 声明上游唯一约束，避免旧 `_sql_constraints` 不再生效。
权限组通过 `res.groups.privilege` 分类，用户的有效权限组读取 `all_group_ids`，显式赋组用 `group_ids`。
`ai_core` 的 token 跟踪引用新 `ai.coworker` / `ai.coworker.session`，不再引用旧 `ai.quest`。

## Business Logic & Data Flow

聊天/业务入口创建 session，核心循环调用所选 `ai.model` 对应的 Provider，
将模型提出的工具调用交给工具注册表和既有权限/人工确认流程。
`cron_tick` 的 `cron.task` 负责后台任务调度、执行日志及单任务失败恢复。
没有重新实现或迁移亚博自研产品编辑确认流程。

## Integration & External APIs

依赖 Odoo 19 的 mail、hr、project、html_editor、base_automation 以及随 fork 提供的 cron_tick。
JSON 控制器使用 `type="jsonrpc"`；聊天 HTTP/SSE 路由保持上游接口。
模型请求通过 httpx；纯模拟测试验证工具调用解析及重试，不使用真实模型账号。
数据库须预先启用 pgvector；Apache AGE 和 web_pwa_push 为可选集成。
缺少 AGE 时不初始化图谱；缺少 web push 时仍保留站内通知和人工确认流程。

## Gotchas & Constraints

OCA ai_tool 和旧 ai_agent 都定义不兼容的 ai.tool，安装钩子拒绝共装。
现有亚博业务库保留 OCA 连接器时，试用必须使用独立数据库。
知识库 SQL 权限辅助函数递归计算继承组，避免 19 的显式组关系漏掉继承的读取权限。
本次是新库试用适配，不包含 Odoo 18 数据迁移、现有业务库替换或完整生产安全审查。
未通过验证的旧模块和行业扩展保持不可安装；不得仅通过改 installable 绕过移植验证。
