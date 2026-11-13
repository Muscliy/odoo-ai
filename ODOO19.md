# Odoo / OCB 19 适配

本分支 `feat/19` 基于 Vertel `18.0` 的 `d55f56556e7a264aa2e182579691e89053cb3f56`。
这里的 18.0 是源码起点，运行目标是 Odoo / OCB 19。

## 支持范围

可安装模块：`ai_agent_core`、`cron_tick`、`ai_core`。
日常聊天和 Agent 平台安装 `ai_agent_core` 即可；`ai_core` 是可选的 LLM 抽象扩展，在 19 上依赖新核心以记录会话；不是核心的必需依赖。
其余模块暂设为 `installable=False`，包括依赖旧 `ai_agent` 的 MCP/HR 等插件。
它们保留源码供后续移植；manifest 版本前缀统一为 19.0 是为了能被 19 的应用扫描识别，不表示已适配。
本分支不是现有 Odoo 18 数据库的升级方案，也不自动迁移 OCA 的配置和历史。

## 独立聊天页的主题

`/ai/chat` 通过独立资源包 `ai_agent_core.assets_chat` 使用已安装后台主题的
品牌色、字体和灰阶变量，不加载整个后台界面。样式位于
`ai_agent_core/static/src/scss/chat.scss`，聊天模板只负责加载该资源包。
新浏览器默认使用浅色，已有深浅色选择继续保留；标签页图标沿用系统公司 Logo。
修改样式后需刷新资源缓存，修改内嵌聊天模板后需重新加载服务。

后端常用 AI 视图通过 `o_ai_kanban`、`o_ai_form`、`o_ai_list` 限定样式范围，
使用 `static/src/scss/backend.scss` 统一信息标签、浅色状态标签和占位图标。
保持原生卡片结构、分组、字段、按钮与权限；该样式不作用于其他业务模块。

## 安装到隔离的 Odoo 19 环境

1. 准备独立数据库和附件目录，使用标准 Odoo 19 的 Python 依赖。
2. 在该环境中安装 `pip install -r /path/to/odoo-ai/requirements-19.txt`。
3. 数据库管理员在目标库执行 `CREATE EXTENSION IF NOT EXISTS vector`。
   本模块不自行提升数据库权限或安装扩展。Apache AGE 是可选项，不安装时跳过图谱初始化。
4. 在 `addons_path` 中加入此仓库根目录，然后安装：

   ```sh
   python odoo-bin -c /path/to/test-19.conf -d isolated_ai19 \
     -i ai_agent_core --without-demo --stop-after-init --no-http --max-cron-threads=0
   ```

5. 正常启动该独立实例，通过用户菜单的 **AI Chat** 打开 `/ai/chat`；
   管理员在 AI 配置中填写 Provider、模型和密钥，并给 Agent/默认助手选择模型。
   不将密钥写入 Git。默认 Provider 数据包含 DeepSeek，但必须自己配置实际可用的模型与账号。

核心知识库需要 PostgreSQL pgvector。文件解析、FAISS、外部 Agent、MCP、推送等集成
还有各自的依赖和部署条件；`requirements-19.txt` 不承诺安装这些可选功能。
`web_pwa_push` 不再是强制依赖，未安装时跳过 web push，站内通知仍可使用。
必需的 `cron_tick` 源码随本 fork 提供，来源和许可见 `PORT_19_SOURCES.md`。

## 与现有 OCA AI 的隔离

OCA `ai_tool` 与 Vertel 都定义 `ai.tool`，结构不兼容。安装钩子会拒绝与 OCA `ai_tool`
或旧版 `ai_agent` 共装（包括待安装状态）。卸载自研 `ai_assistant` 不会自动移除 OCA 的
`ai_connection_openai`、`ai_connection` 和 `ai_tool`。
不要直接在现有业务库共装；替换前需要单独迁移配置、历史和依赖模块。

## 主要适配

- JSON 控制器改为 19 的 `jsonrpc` 类型；取消已移除的 `api.returns`。
- SQL 约束改用 `models.Constraint`，保留原约束名称、定义与提示。
- 权限组通过 `res.groups.privilege` 分类；用户权限判断读取 `all_group_ids`。
- 知识库 SQL 权限函数递归计算继承组，匹配 19 的显式组存储方式。
- 更新搜索视图、用户偏好继承定位、窗口目标和缓存清理 API。
- 员工名称装饰使用 `_compute_display_name`；补充实际必需的 `project` 依赖。
- 必需的模型、控制器导入失败直接暴露，防止模块显示安装成功但实际未注册。

## 验证

在配置好的 Odoo 19 根目录运行（此目录需已在 addons_path 中）：

```sh
python odoo-bin -c /path/to/test-19.conf -d isolated_ai19 \
  -u ai_agent_core,cron_tick --without-demo --stop-after-init --test-enable \
  --test-tags=odoo19_port,/ai_agent_core:TestToolAccessGroups,/ai_agent_core:TestClassifyTransient,/ai_agent_core:TestRetryCountConfiguration,/ai_agent_core:TestRetryEnvelope,/ai_agent_core:TestStreamRetry,/ai_agent_core:TestRetryEventContract,/ai_agent_core:TestBreakerInteraction,/cron_tick \
  --http-port=8076 --max-cron-threads=0
```

覆盖继承组权限、真实数据库唯一约束、OCA 冲突保护、可选推送、员工显示名、
模拟模型工具调用、模型重试、调度失败恢复、资产编译，以及 HTTP/Chrome 后台页面。
浏览器测试需要 Chrome。测试不使用真实模型密钥，不验证线上 DeepSeek 服务。
日志中的故意重复键和除零属于约束/调度恢复测试，最终以测试汇总判定。

原有全量 Ruff C901 检查在上游 `controllers/stream.py::stream` 已有 129 > 113 的失败，
本次未改该方法的控制流或提高阈值；可用相同配置在基线提交复现。
未对所有上游测试、外部集成和生产部署作出验证结论。
