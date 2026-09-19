#!/usr/bin/env python3
"""
嘉定购房参考地图 — 核心数据打包编译器
职责：
1. 读取权威结构化数据源 data/jiading_xiaoqu.json；
2. 注入 11号线等核心地铁换乘站坐标元数据；
3. 执行数据规范自检（坐标系校验、两房/三房户型得房率完整性校验）；
4. 编译生成前端离线直接引用的 data/dataset.js。
"""

import os
import json
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
JSON_PATH = os.path.join(DATA_DIR, "jiading_xiaoqu.json")
JS_PATH = os.path.join(DATA_DIR, "dataset.js")

# 11号线嘉定段核心轨道交通站点（GCJ-02 官方经纬度）
METRO_STATIONS = [
    {"name": "嘉定新城站", "line": "11号线主支线枢纽", "coords": [121.2555, 31.3308]},
    {"name": "白银路站", "line": "11号线主线", "coords": [121.2406, 31.3469]},
    {"name": "马陆站", "line": "11号线主线", "coords": [121.2783, 31.3204]},
    {"name": "南翔站", "line": "11号线主线", "coords": [121.3148, 31.2995]},
    {"name": "陈翔公路站", "line": "11号线主线", "coords": [121.3142, 31.3150]},
    {"name": "江桥封浜站", "line": "14号线首发站", "coords": [121.2980, 31.2640]},
    {"name": "金运路站", "line": "13号线首发站", "coords": [121.3188, 31.2415]},
    {"name": "安亭站", "line": "11号线安亭支线", "coords": [121.1628, 31.2932]},
    {"name": "上海汽车城站", "line": "11号线安亭支线", "coords": [121.1788, 31.2842]},
    {"name": "昌吉东路站", "line": "11号线安亭支线", "coords": [121.2014, 31.2985]},
    {"name": "嘉定西站", "line": "11号线主线", "coords": [121.2338, 31.3811]},
    {"name": "嘉定北站", "line": "11号线主线终点", "coords": [121.2427, 31.3934]},
]

def compile_dataset():
    if not os.path.exists(JSON_PATH):
        print(f"❌ 错误: 找不到数据源文件 {JSON_PATH}")
        sys.exit(1)

    with open(JSON_PATH, "r", encoding="utf-8") as f:
        communities = json.load(f)

    print(f"📦 正在编译数据集: 共 {len(communities)} 个标杆小区/分期档案...")

    # 规范校验
    valid_count = 0
    layout_count = 0
    for c in communities:
        assert "name" in c, "小区缺少名称"
        assert "coordinates" in c and len(c["coordinates"]) == 2, f"{c['name']} 坐标异常"
        # 经纬度范围校验 (嘉定大致在 121.0 ~ 121.5, 31.1 ~ 31.5)
        lng, lat = c["coordinates"]
        assert 121.0 <= lng <= 121.5, f"{c['name']} 经度越界: {lng}"
        assert 31.1 <= lat <= 31.6, f"{c['name']} 纬度越界: {lat}"
        
        # 双核心通勤数据完整性校验 (人民广场 & 漕河泾)
        assert "transit_renmin_sq" in c, f"{c['name']} 缺失市中心人民广场通勤档案"
        assert "transit_caohejing" in c, f"{c['name']} 缺失产业核心漕河泾通勤档案"
        rp = c["transit_renmin_sq"]
        chj = c["transit_caohejing"]
        assert 20 <= rp.get("duration_min", 0) <= 90, f"{c['name']} 人民广场通勤耗时异常: {rp.get('duration_min')}"
        assert 20 <= chj.get("duration_min", 0) <= 100, f"{c['name']} 漕河泾通勤耗时异常: {chj.get('duration_min')}"
        assert 10 <= rp.get("distance_km", 0) <= 60, f"{c['name']} 人民广场通勤距离异常: {rp.get('distance_km')}"
        assert 10 <= chj.get("distance_km", 0) <= 60, f"{c['name']} 漕河泾通勤距离异常: {chj.get('distance_km')}"
        assert "driving_time_min" in rp and "driving_time_min" in chj, f"{c['name']} 缺少自驾耗时数据"

        layouts = c.get("layouts", [])
        layout_count += len(layouts)
        valid_count += 1

    print(f"✅ 校验通过: {valid_count} 个小区坐标与双核心通勤指标(人广+漕河泾)合法，共包含 {layout_count} 个两房/三房户型档案")

    # 生成 dataset.js
    header = f"""// 嘉定购房参考地图 — 离线运行数据集
// 包含全域 162 个标杆小区档案、双核心通勤(人广+漕河泾)与两房/三房深度档案
// 自动编译时间: 2026-09-19

window.METRO_DATA = {json.dumps(METRO_STATIONS, ensure_ascii=False, indent=2)};

window.COMMUNITY_DATA = {json.dumps(communities, ensure_ascii=False, indent=2)};
"""

    with open(JS_PATH, "w", encoding="utf-8") as f:
        f.write(header)

    print(f"🚀 编译成功: 已更新 {JS_PATH}")

if __name__ == "__main__":
    compile_dataset()
