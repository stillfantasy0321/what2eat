# 吃神马（what2eat）

“吃神马”是一个有来源、会保存对话的菜谱 Agent。用户可以直接与 Agent 对话，也可以分页浏览菜谱并在居中弹窗中阅读完整原文。项目以 HowToCook 的 64 篇中文 Markdown 菜谱为预置语料，省去网页抓取、OCR 和大规模人工清洗。

## 功能

- 首页即对话页，顶部只有“对话”和“菜谱”两个入口。
- 对话提供四项快捷能力：获取全部菜谱、按分类查菜、不知道吃什么、推荐 7 天膳食计划。
- DeepSeek 通过 LangChain 工具调用组合菜谱目录、分类、检索和规划能力。
- 菜谱页提供平铺分类、编号分页、右上角上传入口和完整 Markdown 做法。
- 菜谱详情使用居中弹窗，不再使用右侧抽屉；上游来源按钮保留完整原文入口。
- PostgreSQL 保存会话、消息、运行状态和来源快照；`AsyncPostgresStore` 保存显式长期偏好。
- Milvus Lite 保存由阿里云百炼 `text-embedding-v4` 生成的向量。
- 会话支持创建、切换、删除；`PATCH /api/sessions/{id}` 可用于改名。删除使用站内确认框，操作后重新读取列表。

## 技术栈

- Python 3.13、FastAPI、Pydantic、PostgreSQL 17
- LangChain、DeepSeek `deepseek-flash`
- 阿里云百炼 Embedding、Milvus Lite、BM25 混合检索
- Vue 3、TypeScript、Vite、SSE

项目只使用 LangChain，不使用 LlamaIndex。
