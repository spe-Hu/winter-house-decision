# 嘉定购房参考地图 — Agent 规则手册

## 项目定位

本地离线购房辅助工具。纯 HTML + Leaflet，**无框架，无 Node.js 构建，无后端服务器**。

## 关键红线（必读）

### 1. 坐标系与底图对齐规范（最高优先级）
- 所有坐标存储为 GCJ-02（高德火星坐标系），格式 `[经度, 纬度]`；
- Leaflet 渲染标记时必须转换为 `[纬度, 经度]`，且自定义图标锚点 `iconAnchor` **必须居中**（如 `[24, 24]`），严禁底部锚定导致视觉偏北；
- **绝对准则**：所有图钉必须与高德底图上**印刷的小区文字中心 100% 紧密耦合对齐**；
- **严禁主观推演坐标**：严禁大模型通过道路门牌机械外推经纬度（曾发生中信泰富误套白银路门牌偏离 1.8km、二三期落入紫气东来公园的严重事故）。所有坐标必须通过 `scripts/verify_all_phases.py` 经高德官方住宅类 POI（`types=120300`）核验为 0 米误差；
- 严禁盲目执行全量 WGS-84/GCJ-02 批量平移，避免已对齐坐标发生二次漂移。

### 2. 安全门禁红线
- 访问口令严格锁定为 `9802`，前端必须采用单向加盐 SHA-256（安全散列算法）哈希校验；
- 严禁在任何前端 HTML/JS 源码中残留明文口令或弱哈希。

### 3. 数据真相源与交付前流水线
- **唯一结构化真相源**：`data/jiading_xiaoqu.json`；
- **交付前唯一质量门禁命令**：修改代码或数据后，**必须执行并通过 `./scripts/run_delivery_workflow.sh`**（6 大关卡全绿方可交付）；
- `data/dataset.js` 由构建脚本自动生成，**严禁手动编辑**；
- 户型图必须经 `data/floorplan_catalog.json` 物理房间数断言（两房实测2卧，三房实测3卧，严禁同图）；
- 学区划分必须以 `data/school_ground_truth.json` 2026 官方文字版为权威真值，严禁主观猜测。

### 4. 底图双图层支持
- 矢量底图采用高德官方最新全要素端点（`style=7`）；
- 卫星影像采用高德官方影像 + 注记透明叠加（`style=6` + `style=8`）；
- 必须保持免 API Key 离线公开可用特性。

### 5. 图片本地化与交互防遮挡
- 户型图统一存放于 `assets/floorplans/<house_id>.jpg`，本地相对路径写入 `floor_plan_local` 字段；
- 双栏分屏联动模式下单选表格行仅触发地图飞渡高亮，严禁弹出右侧抽屉遮挡表格；
- 详情工作台必须采用 880px 居中模态卡片，支持键盘左右箭头环形翻页对比。

## 常用命令速查

| 场景 | 命令 |
|---|---|
| **交付前全量质量工作流 (推荐)** | `./scripts/run_delivery_workflow.sh` |
| **全量端到端自动化回归测试** | `python3 scripts/verify_all_regression.py` |
| **官方双学区真值对齐与校验** | `python3 scripts/align_school_ground_truth.py` |
| **多源立体交通噪音拓扑测算** | `python3 scripts/spatial_noise_engine.py` |
| **高德官方 POI 0米误差核验** | `python3 scripts/verify_all_phases.py` |
| **Cloudflare Pages 全球极速发布** | `./scripts/deploy_cloudflare.sh` |

## 深入文档指南

| 文档 | 受众与内容 |
|---|---|
| [README.md](file:///Users/wentao.hu/Documents/HomePage/00-projects/00-doing/买房参考软件/README.md) | 快速启动、目录结构、全域 140 个小区覆盖概况与线上部署说明 |
| [docs/architecture.md](file:///Users/wentao.hu/Documents/HomePage/00-projects/00-doing/买房参考软件/docs/architecture.md) | 系统架构、Leaflet 居中渲染、高德免 Key 瓦片机制与多维交互防遮挡体系 |
| [docs/data-guide.md](file:///Users/wentao.hu/Documents/HomePage/00-projects/00-doing/买房参考软件/docs/data-guide.md) | 小区模型、双学区档案、得房率与两房/三房户型规范 |
| [docs/runbook.md](file:///Users/wentao.hu/Documents/HomePage/00-projects/00-doing/买房参考软件/docs/runbook.md) | 运维手册、高德 POI 抓取工作流、自动化核验与故障排查 |
| [docs/pre_delivery_workflow_sop.md](file:///Users/wentao.hu/Documents/HomePage/00-projects/00-doing/买房参考软件/docs/pre_delivery_workflow_sop.md) | 交付前 6 步自动化流水线、熔断机制与 9 大回归测试场景矩阵 |
| [docs/school_district_ground_truth_sop.md](file:///Users/wentao.hu/Documents/HomePage/00-projects/00-doing/买房参考软件/docs/school_district_ground_truth_sop.md) | 嘉定区 2026 官方中小学学区划分权威真值库、历史错配纠偏与新房源核验规范 |
| [docs/multi_source_noise_evaluation_sop.md](file:///Users/wentao.hu/Documents/HomePage/00-projects/00-doing/买房参考软件/docs/multi_source_noise_evaluation_sop.md) | 11号线地上高架轻轨、胜辛路主干道、S5 高速多源立体交通噪音几何拓扑评估标准 |
| [docs/decision-system-design.md](file:///Users/wentao.hu/Documents/HomePage/00-projects/00-doing/买房参考软件/docs/decision-system-design.md) | 16维加权决策系统、多维表格十字交叉吸附与多模态数据真值治理 |


