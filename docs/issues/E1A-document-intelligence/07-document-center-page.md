# 1A.3.1 — Document Center Page
- **Epic:** E1A Document Intelligence
- **Labels:** `frontend`, `document`, `phase-1a`
- **Depends on:** 1A.1.1 (Document Upload API v1 Freeze)

## 描述

实现文档管理中心前端页面。这是 E1A 冻结 Document API v1 后的前端消费入口，提供拖拽上传、文档列表、实时状态追踪、文档预览和 WebSocket 实时更新能力。

页面核心交互：
1. **拖拽上传区** — 支持拖拽 PDF 文件到上传区域，显示上传进度条，上传完成后自动刷新列表
2. **文档列表** — 表格展示当前项目下所有文档，列含文件名、大小、上传时间、处理状态（彩色 Badge）、页数；支持按状态过滤（全部/Pending/Processing/Ready/Failed）
3. **状态实时更新** — WebSocket 订阅 `DocumentProcessing` / `DocumentReady` / `DocumentFailed` 事件，对应行状态 Badge 实时刷新，无需手动轮询
4. **文档预览** — 点击文档行展开预览面板，显示提取的元数据（公司名/年度/报表类型）和文本片段预览（前 3 个 Chunk）
5. **删除确认** — 删除按钮弹窗确认后调用 DELETE API

遵循 **Backend Capability First Rule**：前端基于冻结的 `GET/POST/DELETE /api/v1/documents/*` 开发，可使用 MSW Mock 先行。

## Acceptance Criteria

- [ ] 拖拽上传区域：支持拖拽 .pdf 文件 / 点击选择文件
- [ ] 上传进度条（文件大小 → 百分比）
- [ ] 上传成功后列表自动刷新，新文档出现在顶部
- [ ] 文档列表表格列：文件名 / 大小（格式化 MB） / 上传时间 / 状态 Badge / 页数 / 操作（删除）
- [ ] 状态 Badge 颜色映射：PENDING=gray / PARSING+OCR+CHUNKING+EMBEDDING=blue(脉冲动画) / READY=green / FAILED=red
- [ ] WebSocket 连接 `/ws/documents/{project_id}`，事件驱动状态更新
- [ ] 状态过渡动画：Processing 状态含脉冲指示器
- [ ] 点击行展开预览面板：元数据卡片 + 文本片段（前 3 个 Chunk 的 content[0:200]）
- [ ] 删除按钮 → 确认对话框 → 调用 DELETE API → 行移除
- [ ] 空状态：无文档时显示插图 + 提示"拖拽 PDF 文件到此处上传"
- [ ] 错误状态：FAILED 文档行显示错误信息 Tooltip
- [ ] 响应式布局：移动端列表转为卡片布局
- [ ] 暗色模式兼容

## I/O 接口

N/A（前端页面，消费 E1A 冻结的 Document API v1）

### API 依赖

| 端点 | 用途 |
|------|------|
| `POST /api/v1/documents` | 上传文档（multipart/form-data） |
| `GET /api/v1/documents?project_id=...` | 文档列表（分页 + 状态过滤） |
| `GET /api/v1/documents/{id}` | 文档详情（含 metadata + chunks 预览） |
| `DELETE /api/v1/documents/{id}` | 删除文档 |
| `WS /ws/documents/{project_id}` | WebSocket 事件流（DocumentProcessing / DocumentReady / DocumentFailed） |

### 组件树

```
DocumentCenterPage
├── UploadZone (拖拽上传 + 文件选择)
├── StatusFilter (Tab: 全部 | Pending | Processing | Ready | Failed)
├── DocumentTable
│   ├── DocumentRow (文件名/大小/时间/状态Badge/页数/删除按钮)
│   └── DocumentPreviewPanel (展开: 元数据卡片 + Chunk 文本预览)
└── EmptyState (无文档时的占位图)
```
