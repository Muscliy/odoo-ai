# 中文适配扫描与验证

扫描范围为 `vertel_ai/` 全部 20 个模块。当前 Odoo 19 支持的模块为 `ai_agent_core`、`ai_core`、`cron_tick`。其余模块的 manifest 为 `installable=False`，属于保留待移植源码。

本轮修改覆盖当前可运行模块的内置数据与运行提示；未将历史模块标记为已完成汉化。

## 静态扫描结果

| 模块 | Odoo 19 可安装 | 文案候选 | 未覆盖候选 |
|---|---|---:|---:|
| agent_pi | 否 | 235 | 235 |
| ai_agent | 否 | 1060 | 1060 |
| ai_agent_context | 否 | 45 | 45 |
| ai_agent_core | 是 | 3694 | 0 |
| ai_agent_core_academic | 否 | 0 | 0 |
| ai_agent_core_strategy | 否 | 0 | 0 |
| ai_agent_hr | 否 | 27 | 27 |
| ai_agent_mcp | 否 | 68 | 68 |
| ai_agent_pgvector | 否 | 22 | 22 |
| ai_agent_seo | 否 | 14 | 14 |
| ai_agent_transcript | 否 | 36 | 36 |
| ai_agent_trend | 否 | 103 | 103 |
| ai_agent_zabbix | 否 | 28 | 28 |
| ai_core | 是 | 32 | 0 |
| ai_mail_e_avrop | 否 | 13 | 13 |
| ai_onboarding | 否 | 16 | 16 |
| ai_pi_mcp | 否 | 36 | 36 |
| cron_tick | 是 | 109 | 0 |
| gamification_ai | 否 | 7 | 7 |
| pi_mesh | 否 | 137 | 137 |

候选不是人工确认的缺陷数。扫描使用 Odoo 的 XML 文案提取逻辑，并检查 Python 字段标题、帮助、选择项、翻译标记及工具说明。代码注释、日志、接口键、模型名、枚举值、路径和第三方专名不作为待汉化文案。动态拼接文案、数据库自定义内容和全部浏览器状态仍需运行验证。

历史模块仍有未覆盖的瑞典语和英文候选，集中在旧 `ai_agent`、`agent_pi`、`pi_mesh` 及行业扩展。它们没有随本轮升级启用，不能把当前三个模块的覆盖结果解读为全仓库无外语。

## 本轮实现

- 20 项内置技能：源文件中的说明、操作步骤、中文触发词和可读名称；保留 `/odoo-core` 等技术名称。
- 44 个内置工具说明及 75 条参数说明；技能加载、任务规划工具、XML 内嵌工具的参数与反馈也直接使用中文。
- 73 处静态 API/工具错误提示及 16 条恢复建议和处理说明直接改为中文，保留错误结构、状态码和参数名。
- AI 员工人设默认中文；中文账号的会话标题和摘要使用中文；记忆提取跟随用户语言。
- 中文业务短语参与工具选择，验证员工查询优先命中 `odoo_search`。
- 安装与升级最后执行字段级同步：旧值指纹一致才更新，按 XML ID 或 builtin_name 定位，保留改名工具和自定义字段。普通非 noupdate 的 XML 数据仍沿用 Odoo 原有升级管理规则。
- 记忆分类和知识资料类型使用中文显示名，底层技术标识保持不变。

## 验证

- 新增 9 项无数据库行为测试，覆盖字段级保留、幂等、已改名工具、参数与审批契约、中文路由、嵌入工具错误和中文标题。
- 原有 13 项中文界面测试、4 项空回复测试和 6 项 Odoo 任务/技能工具状态测试通过。
- 在本机隔离数据库 `codex_vertel_zh_20261113` 完成模块升级，验证 20 项技能、中文显示名、参数与说明、工具迁移和技能表单编译。测试副本的 Provider 密钥已清空并指向本机不可用端口；未调用真实模型。
- 未对当前使用中的数据库执行升级，未部署或推送。

重新扫描（在 Odoo 根目录）：

```sh
.venv/bin/python -m external_addons.vertel_ai.scripts.audit_zh --output /tmp/vertel_ai_zh_audit.json
```

测试命令（Odoo 根目录）：

```sh
.venv/bin/python -m unittest discover -s external_addons/vertel_ai/ai_agent_core/tests -p test_builtin_chinese.py
.venv/bin/python -m unittest discover -s external_addons/vertel_ai/ai_agent_core/tests -p test_ui_chinese.py
.venv/bin/python -m unittest discover -s external_addons/vertel_ai/ai_agent_core/tests -p test_empty_reply_localization.py
```

Odoo 隔离库验证使用临时配置执行 `odoo-bin -u ai_agent_core --stop-after-init --no-http --load-language=zh_CN`；
另以 `--test-enable --test-tags=/ai_agent_core:TestPlanningToolsOwnTheirState,/ai_agent_core:TestSpecialistsHaveSeparateTodos` 运行 6 项数据库测试。
配置中的模型密钥已清空，不保存或输出凭据。临时数据库和含连接凭据的配置在验证后清理。
