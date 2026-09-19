# 嘉定购房参考地图 — 运维与数据维护手册

## 1. 日常维护命令速查

| 操作场景 | 执行命令 | 预期结果 |
| :--- | :--- | :--- |
| **交付前自动化全量流水线 (核心推荐)** | `./scripts/run_delivery_workflow.sh` | 自动执行 6 步质量门禁（真值+编译+回归测试），全绿方可交付 |
| **全量端到端自动化回归测试** | `python3 scripts/verify_all_regression.py` | 静态安全真值核验 + Playwright 9 大全场景自动化测试 |
| **2026 官方学区真值对齐** | `python3 scripts/align_school_ground_truth.py` | 对口小学+初中双学区与官方真值名录及四至范围严格对齐 |
| **多源立体交通噪音几何拓扑测算** | `python3 scripts/spatial_noise_engine.py` | 测算轨交高架、主干道、高速垂距与一票否决标记 |
| **全量高德官方坐标核验** | `python3 scripts/verify_all_phases.py` | 调用高德 API 检查全量核心小区误差是否为 0 米 |
| **一键编译构建离线数据包** | `python3 scripts/build_dataset.py` | 校验合法性并生成 `data/dataset.js` |
| **Cloudflare Pages 全球一键部署** | `./scripts/deploy_cloudflare.sh` | 一键打包 dist 目录并发布至 Cloudflare Pages 全球 CDN |
| **高德单个 POI 查询抓取** | `python3 scripts/gaode_fetcher.py` | 返回严格纯住宅类型的标准备案名与坐标 |

## 2. 扩充或修改小区标准工作流

当需要新增小区或更新已有小区数据时，**必须严格按以下步骤执行**：

### 第一步：获取高德官方严格 POI
严禁依靠大模型猜测坐标！使用 `scripts/gaode_fetcher.py` 获取官方备案。

### 第二步：编辑 `data/jiading_xiaoqu.json`
将官方获取的标准名称、备案门牌、坐标 `[经度, 纬度]` 以及两房/三房户型档案补充进 `data/jiading_xiaoqu.json`。

### 第三步：核验 2026 官方学区与户型图物理真值
- 户型图两房必须实测 2 间卧室，三房必须实测 3 间卧室（录入 `data/floorplan_catalog.json`）；
- 学校必须比对 `data/school_ground_truth.json` 中的四至道路边界或对口居委，严禁主观填写。

### 第四步：执行交付前全流程自动化质量流水线
```bash
./scripts/run_delivery_workflow.sh
```
确保终端输出 `🎉 恭喜！交付前全流程 6 大质量关卡全部通过`。若有任何断言失败，立即排查修复。

## 3. 故障排查（Troubleshooting）

### 现象 1：前端地图刷新后坐标未更新
- **原因**：修改了 JSON 但未执行 `scripts/build_dataset.py` 编译，或浏览器缓存了 `data/dataset.js`。
- **解决**：运行 `python3 scripts/build_dataset.py` 并使用 `Cmd + Shift + R` 强制刷新浏览器。

### 现象 2：图钉漂移，与底图印刷文字不重合
- **原因**：错误使用了商办/售楼处坐标，或门牌号处于同名道路远端。
- **解决**：运行 `python3 scripts/verify_all_phases.py`，查看高德官方严格纯住宅（`types=120300`）真实地址与坐标。

### 现象 3：户型图加载裂图
- **原因**：`assets/floorplans/` 下缺少对应的本地图片文件。
- **解决**：确保 `floor_plan_local` 指向有效的本地静态文件路径，禁止外链。
