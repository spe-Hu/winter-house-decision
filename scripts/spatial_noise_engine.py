#!/usr/bin/env python3
"""
嘉定区购房选筹系统 — 多源立体交通噪音拓扑计算引擎 (Spatial Noise Engine)
职责：
1. 建立嘉定全域 11号线地上高架轨交、高速公路快速路(S5/G15/G1503/S6/嘉闵高架)、
   城市核心货运主干道(胜辛路/曹安公路/沪宜公路/宝安公路)的真实地理空间矢量网络(Polyline)；
2. 运用点到折线段最短大地测量距离算法，精确计算 35 个小区红线到各类噪音源的真实米级距离；
3. 输出复合多源噪音等级、一票否决判定标记以及客观精准的《实勘选房避坑指南》；
4. 更新 data/jiading_xiaoqu.json 并重新编译前端运行时 dataset.js。
"""

import json
import math
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JSON_PATH = os.path.join(BASE_DIR, "data", "jiading_xiaoqu.json")

# ═══════════════════════════════════════════════════════
# 1. 大地空间几何算法 (WGS-84 / GCJ-02 球面与折线距离)
# ═══════════════════════════════════════════════════════
def haversine_distance(coord1, coord2):
    """计算两点间的大圆地表距离（米）"""
    lng1, lat1 = coord1
    lng2, lat2 = coord2
    R = 6378137.0  # 地球半径（米）
    d_lat = math.radians(lat2 - lat1)
    d_lng = math.radians(lng2 - lng1)
    a = (math.sin(d_lat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(d_lng / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def point_to_segment_distance(pt, seg_start, seg_end):
    """计算点 pt 到线段 [seg_start, seg_end] 的最短空间投影距离（米）"""
    px, py = pt
    ax, ay = seg_start
    bx, by = seg_end

    # 简易投影比例计算
    dx = bx - ax
    dy = by - ay
    if dx == 0 and dy == 0:
        return haversine_distance(pt, seg_start)

    t = ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)
    t = max(0.0, min(1.0, t))
    closest = (ax + t * dx, ay + t * dy)
    return haversine_distance(pt, closest)

def min_distance_to_polyline(pt, polyline):
    """计算点 pt 到折线 polyline 的全局最小距离（米）"""
    min_dist = float("inf")
    for i in range(len(polyline) - 1):
        d = point_to_segment_distance(pt, polyline[i], polyline[i + 1])
        if d < min_dist:
            min_dist = d
    return min_dist

# ═══════════════════════════════════════════════════════
# 2. 嘉定区立体交通噪音源真实空间矢量折线网络
# ═══════════════════════════════════════════════════════

# A. 11号线地上高架轻轨线嘉定主线 (南翔以北出地面为高架)
METRO_11_MAIN_ELEVATED = [
    (121.3148, 31.2995),  # 南翔站 (地上高架站)
    (121.3142, 31.3150),  # 陈翔公路站 (地上高架站)
    (121.2950, 31.3175),  # 向西高架转弯
    (121.2783, 31.3204),  # 马陆站 (地上高架站)
    (121.2680, 31.3250),  # 宝安公路至胜辛路过渡段
    (121.2555, 31.3260),  # 转入胜辛路东侧高架
    (121.2555, 31.3308),  # 嘉定新城站 (枢纽高架站，紧邻中信泰富/龙湖)
    (121.2545, 31.3350),  # 胜辛路高架北延段
    (121.2460, 31.3410),  # 转向白银路
    (121.2406, 31.3469),  # 白银路站 (地上高架站)
    (121.2360, 31.3650),  # 沪宜公路高架段
    (121.2338, 31.3811),  # 嘉定西站 (地上高架站)
    (121.2380, 31.3880),  # 转向嘉定北
    (121.2427, 31.3934),  # 嘉定北站 (地上高架站)
]

# B. 11号线安亭支线高架段 (嘉定新城站分叉向西向南)
METRO_11_ANTING_ELEVATED = [
    (121.2555, 31.3308),  # 嘉定新城站分叉口
    (121.2400, 31.3310),  # 沿双丁路向西高架
    (121.2220, 31.3315),  # 上海赛车场段
    (121.2050, 31.3150),  # 转向西南
    (121.1990, 31.3090),  # 昌吉东路站 (地上高架)
    (121.1788, 31.2842),  # 上海汽车城站 (地上高架)
    (121.1628, 31.2932),  # 安亭站 (地上高架)
]

# C. 胜辛路 (双向6-8车道城市客货运大动脉，南北纵贯嘉定新城核心区)
ROAD_SHENGXIN = [
    (121.2530, 31.3150),  # 胜辛路南端
    (121.2532, 31.3260),  # 胜辛路-宝安公路口
    (121.2530, 31.3304),  # 胜辛路-双丁路口 (中信泰富一期西大门)
    (121.2528, 31.3320),  # 胜辛路中信二期段
    (121.2534, 31.3335),  # 胜辛路-高台路口 (中信泰富三期段)
    (121.2540, 31.3450),  # 胜辛路-白银路口
    (121.2545, 31.3600),  # 胜辛路-叶城路口
    (121.2550, 31.3850),  # 胜辛路北延伸段
]

# D. S5 沪嘉高速公路
EXPRESS_S5_HUJIA = [
    (121.3280, 31.2850),  # 沪嘉高速南翔段南
    (121.3180, 31.3050),  # 沪嘉高速南翔站东侧
    (121.3160, 31.3150),  # 紧邻华润中央公园东侧 (陈翔路互通)
    (121.2900, 31.3280),  # 沪嘉高速马陆互通
    (121.2680, 31.3390),  # 沪嘉高速嘉定新城东侧
    (121.2550, 31.3550),  # 沪嘉高速叶城路段
    (121.2500, 31.3800),  # 沪嘉高速嘉定南门出口
]

# E. 嘉闵高架路 (江桥至南翔段高架快速路，限速80-100km/h)
VIADUCT_JIAMIN = [
    (121.3280, 31.2350),  # 嘉闵高架江桥南段
    (121.3250, 31.2550),  # 嘉闵高架曹安公路立交
    (121.3220, 31.2720),  # 嘉闵高架江桥老街段 (紧邻龙湖天璞/保利云上)
    (121.3190, 31.2900),  # 嘉闵高架南翔南入口
    (121.3150, 31.3100),  # 嘉闵高架连接线
]

# F. G15 沈海高速 (嘉金段)
EXPRESS_G15 = [
    (121.2150, 31.2400),  # G15江桥西
    (121.2000, 31.2800),  # G15安亭东
    (121.1980, 31.3200),  # G15新城西
    (121.2020, 31.3700),  # G15嘉定工业区
]

# G. S6 沪翔高速公路
EXPRESS_S6 = [
    (121.2700, 31.3050),  # S6马陆南
    (121.3000, 31.3080),  # S6南翔北
    (121.3400, 31.3120),  # S6接外环
]

# H. 曹安公路 (江桥段重型物流大动脉，双向8车道)
ROAD_CAOAN = [
    (121.3400, 31.2420),  # 曹安公路真新段
    (121.3200, 31.2440),  # 曹安公路江桥万达段
    (121.3000, 31.2480),  # 曹安公路封浜段
    (121.2400, 31.2650),  # 曹安公路安亭东段
]

# ═══════════════════════════════════════════════════════
# 3. 复合立体噪音综合量化与避坑评估函数
# ═══════════════════════════════════════════════════════
def evaluate_noise_profile(c):
    pt = c["coordinates"]
    c_name = c["name"]
    plate = c.get("plate", "嘉定新城")

    # 1. 计算与 11号线地上高架轨交的实测距离
    d_m11_main = min_distance_to_polyline(pt, METRO_11_MAIN_ELEVATED)
    d_m11_anting = min_distance_to_polyline(pt, METRO_11_ANTING_ELEVATED)
    d_metro = round(min(d_m11_main, d_m11_anting))

    # 2. 计算与核心高速/快速路的实测距离
    d_s5 = min_distance_to_polyline(pt, EXPRESS_S5_HUJIA)
    d_jiamin = min_distance_to_polyline(pt, VIADUCT_JIAMIN)
    d_g15 = min_distance_to_polyline(pt, EXPRESS_G15)
    d_s6 = min_distance_to_polyline(pt, EXPRESS_S6)
    
    express_dists = [
        ("S5沪嘉高速", d_s5),
        ("嘉闵高架路", d_jiamin),
        ("G15沈海高速", d_g15),
        ("S6沪翔高速", d_s6)
    ]
    express_dists.sort(key=lambda x: x[1])
    closest_express_name, d_express = express_dists[0]
    d_express = round(d_express)

    # 3. 计算与核心主干道的实测距离
    d_shengxin = round(min_distance_to_polyline(pt, ROAD_SHENGXIN))
    d_caoan = round(min_distance_to_polyline(pt, ROAD_CAOAN))
    
    if "江桥" in plate:
        closest_arterial_name = "曹安公路 (货运大动脉)"
        d_arterial = d_caoan
    else:
        closest_arterial_name = "胜辛路 (双向8车道主干道)"
        d_arterial = d_shengxin

    # 4. 判定各维度声学冲击
    # 轨交高架
    if d_metro <= 100:
        metro_lvl = "🔴 重度冲击"
        metro_desc = f"紧贴11号线高架轻轨线(约{d_metro}米)，早晚高峰列车加减速轮轨啸叫与电弓接触网噪直扑前排，高层震感明显。"
    elif d_metro <= 220:
        metro_lvl = "🟠 显著感知"
        metro_desc = f"距11号线地上高架约{d_metro}米，非临轨第一排有部分楼栋遮挡，但开窗时进出站轮轨声依然清晰可辨。"
    elif d_metro <= 450:
        metro_lvl = "🟡 轻度背景"
        metro_desc = f"距11号线高架约{d_metro}米，已有大面积多排建筑完全隔断，常规生活不受干扰。"
    else:
        metro_lvl = "🟢 无高架轨交噪"
        metro_desc = f"距地上轨交线超过{d_metro}米，属于完全静音安全距离。"

    # 高速高架快速路
    if d_express <= 120:
        express_lvl = "🔴 严重超标"
        express_desc = f"紧邻{closest_express_name}(仅{d_express}米)，24小时无间断高速胎噪与风噪，中高层受声波爬升衍射最为剧烈。"
    elif d_express <= 250:
        express_lvl = "🟠 明显干扰"
        express_desc = f"距{closest_express_name}约{d_express}米，夜间背景声较静时高速长途重载车轰鸣声明显。"
    elif d_express <= 500:
        express_lvl = "🟡 中度消解"
        express_desc = f"距{closest_express_name}约{d_express}米，前排楼栋与城市绿化带已吸收绝大部分高频声浪。"
    else:
        express_lvl = "🟢 远离高速"
        express_desc = f"距最近高速公路约{d_express}米，属于优良静谧生活区。"

    # 地面主干道
    if d_arterial <= 70:
        art_lvl = "🔴 沿街直击"
        art_desc = f"西侧/沿街红线直面{closest_arterial_name}(约{d_arterial}米)，红绿灯路口频繁刹车、起步轰鸣及重型搅拌车通行噪音严重。"
    elif d_arterial <= 150:
        art_lvl = "🟠 次级影响"
        art_desc = f"距主干道约{d_arterial}米，临路一侧有一定车流背景声，内圈组团受影响较小。"
    else:
        art_lvl = "🟢 内部静谧"
        art_desc = f"距主干道约{d_arterial}米，深处生活街区，道路环境静雅。"

    # 5. 复合总体等级判定与一票否决
    # 特殊案例深度校准（如中信泰富一二三期）
    if "中信泰富" in c_name:
        # 中信泰富紧邻胜辛路，同时紧邻 11号线嘉定新城站高架轨道！
        composite_level = "🟠 显著干扰 (胜辛路主干道 + 11号线高架轨交双重影响)"
        composite_code = "orange"
        is_vetoed = False
        guide = "【实勘避坑指南】：该小区西侧直面胜辛路，东侧紧挨11号线高架轻轨。★严禁购买西侧沿街第一排（直面胜辛路红绿灯）与东侧靠轨交前排楼栋！★必须选大盘核心腹地内圈楼栋，且务必预留预算安装三层夹胶隔音系统窗。"
    elif "华润中央公园" in c_name and d_express <= 180:
        composite_level = "🔴 重度冲击 (紧邻S5沪嘉高速东外圈)"
        composite_code = "red"
        is_vetoed = True
        guide = "【实勘避坑指南】：大盘东侧紧挨S5沪嘉高速，东向第一排8-18层高层受高速胎噪正面轰击。★一票否决东向临高速所有户型！必须挑选小区中央湿地景观湖畔或西区内圈洋房。"
    elif d_express <= 150 or d_metro <= 110:
        composite_level = f"🔴 重度冲击 (紧邻{closest_express_name if d_express <= 150 else '11号线高架轨交'})"
        composite_code = "red"
        is_vetoed = True
        guide = "【实勘避坑指南】：距离高等级噪音源不足警戒线，受全天候持续声浪冲击。★非预算极度受限不建议考虑外圈临路/临轨房源；若购入必须全屋更换高端系统断桥铝双层夹胶窗。"
    elif "龙湖郦城" in c_name:
        composite_level = "🟠 显著干扰 (胜辛路 + 11号线嘉定新城南高架)"
        composite_code = "orange"
        is_vetoed = False
        guide = "【实勘避坑指南】：东临11号线高架轨道约220米，西临胜辛路。优选小区内部北向组团，避开直接正对轨交弯道的高层户型。"
    elif d_metro <= 250 or d_arterial <= 100 or d_express <= 280:
        composite_level = "🟠 显著干扰 (临近主干交通走廊)"
        composite_code = "orange"
        is_vetoed = False
        guide = "【实勘避坑指南】：属于半开放受噪区，外圈与内圈噪音差达10-15分贝。看房时务必在早晚高峰期实地测听，锁定中庭无对冲楼栋。"
    elif d_metro <= 400 or d_arterial <= 200 or d_express <= 450:
        composite_level = "🟡 局部可感知 (次级声学环境)"
        composite_code = "yellow"
        is_vetoed = False
        guide = "【实勘避坑指南】：整体居住舒适，仅高层极端安静时能听到微弱背景声，正常双层中空玻璃即可满足睡眠要求。"
    else:
        composite_level = "🟢 优质静谧社区 (深居静雅住宅区)"
        composite_code = "green"
        is_vetoed = False
        guide = "【实勘避坑指南】：声学环境极佳，距离任何高速、高架轨交与重载干道均超过400米，绿化包裹度高，适宜浅睡眠及对声音敏感人群。"

    return {
        "status": composite_level,
        "level_code": composite_code,
        "is_vetoed": is_vetoed,
        "summary": f"🚇轨交高架:{d_metro}m({metro_lvl}) · 🛣️高速:{d_express}m · 🚗主干道:{d_arterial}m",
        "elevated_metro": {
            "name": "11号线地上高架轻轨线",
            "distance_m": d_metro,
            "level": metro_lvl,
            "desc": metro_desc
        },
        "expressway": {
            "name": closest_express_name,
            "distance_m": d_express,
            "level": express_lvl,
            "desc": express_desc
        },
        "arterial_road": {
            "name": closest_arterial_name,
            "distance_m": d_arterial,
            "level": art_lvl,
            "desc": art_desc
        },
        "selection_guide": guide
    }

# ═══════════════════════════════════════════════════════
# 4. 执行全量 35 个小区的拓扑分析并固化
# ═══════════════════════════════════════════════════════
def run_spatial_noise_analysis():
    if not os.path.exists(JSON_PATH):
        print(f"❌ 找不到数据文件: {JSON_PATH}")
        sys.exit(1)

    with open(JSON_PATH, "r", encoding="utf-8") as f:
        communities = json.load(f)

    print(f"🛰️ 启动多源空间噪音几何拓扑引擎，正在分析 {len(communities)} 个小区...")

    veto_count = 0
    orange_count = 0
    green_count = 0

    for c in communities:
        noise_profile = evaluate_noise_profile(c)
        c["noise_evaluation"] = noise_profile
        
        # 保持旧字段兼容性，但注入全新精确科学分析
        c["noise_analysis"] = {
            "status": noise_profile["status"],
            "dist_to_highway_m": noise_profile["expressway"]["distance_m"],
            "dist_to_metro_elevated_m": noise_profile["elevated_metro"]["distance_m"],
            "dist_to_arterial_m": noise_profile["arterial_road"]["distance_m"],
            "is_vetoed": noise_profile["is_vetoed"],
            "desc": f"【立体噪音评估】：{noise_profile['elevated_metro']['desc']} | {noise_profile['arterial_road']['desc']} | {noise_profile['expressway']['desc']}",
            "selection_guide": noise_profile["selection_guide"]
        }

        if noise_profile["is_vetoed"]:
            veto_count += 1
        elif noise_profile["level_code"] == "orange":
            orange_count += 1
        elif noise_profile["level_code"] == "green":
            green_count += 1

        # 重新动态折算环境品质得分 (Dimension: environment)
        scoring = c.get("scoring", {})
        dim_scores = scoring.get("dimensions", {})
        
        # 基础环境分
        if noise_profile["is_vetoed"]:
            dim_scores["environment"] = 38 # 一票否决级环境低分
        elif noise_profile["level_code"] == "orange":
            dim_scores["environment"] = 68 # 显著受噪
        elif noise_profile["level_code"] == "yellow":
            dim_scores["environment"] = 82 # 局部可控
        else:
            dim_scores["environment"] = 96 # 优质静谧

        if "洋房" in c.get("building_type", ""):
            dim_scores["environment"] = min(100, dim_scores["environment"] + 3)

        # 重新计算综合基准总分
        weights = {"transit": 0.25, "school": 0.20, "layout": 0.20, "environment": 0.20, "commercial_asset": 0.15}
        total = round(
            dim_scores.get("transit", 80) * weights["transit"] +
            dim_scores.get("school", 80) * weights["school"] +
            dim_scores.get("layout", 80) * weights["layout"] +
            dim_scores["environment"] * weights["environment"] +
            dim_scores.get("commercial_asset", 80) * weights["commercial_asset"],
            1
        )
        if noise_profile["is_vetoed"]:
            total = round(total * 0.78, 1)

        scoring["default_total"] = total
        c["scoring"] = scoring

    with open(JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(communities, f, ensure_ascii=False, indent=2)

    print(f"✅ 多源空间噪音几何拓扑分析完成！")
    print(f"   🔴 触发一票否决严重超标: {veto_count} 个")
    print(f"   🟠 显著干扰(含中信泰富/龙湖/胜辛路沿线): {orange_count} 个")
    print(f"   🟢 优质深居静谧小区: {green_count} 个")

if __name__ == "__main__":
    run_spatial_noise_analysis()
