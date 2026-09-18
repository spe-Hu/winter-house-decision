#!/usr/bin/env python3
"""
优化版高德地图全能版（gaode-map-pro）批量抓取器
采用双层漏斗过滤算法：
1. 优先带 types="120300" (纯住宅) 检索；
2. 若未命中，通过 input_tips 联想获取高德官方标准地名；
3. 降级为关键字检索并按住宅类型优先排序。
"""

import sys
import json
import subprocess

GAODE_SKILL_SCRIPT = "/Users/wentao.hu/.workbuddy/skills/gaode-map-pro__skillhub/scripts/main.py"

def query_gaode_poi(community_name, city="上海", district="嘉定区"):
    def run_cmd(tool, params):
        cmd = [sys.executable, GAODE_SKILL_SCRIPT, tool, json.dumps(params, ensure_ascii=False)]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode == 0:
            try:
                return json.loads(res.stdout).get("data", {})
            except:
                pass
        return {}

    # 1. 第一梯队：带 types=120300 的严格住宅检索
    d = run_cmd("poi_search", {"keywords": community_name, "city": city, "types": "120300"})
    pois = d.get("pois", [])
    if pois:
        p = pois[0]
        lng, lat = map(float, p["location"].split(","))
        return {
            "name": p["name"],
            "address": p.get("address", ""),
            "coordinates": [round(lng, 4), round(lat, 4)],
            "strategy": "严格住宅POI"
        }

    # 2. 第二梯队：input_tips 联想获取官方案名
    tips_data = run_cmd("input_tips", {"keywords": community_name, "city": city})
    tips = tips_data.get("tips", [])
    for t in tips:
        loc = t.get("location")
        if loc and isinstance(loc, str) and "," in loc:
            # 检查是否有坐标
            lng, lat = map(float, loc.split(","))
            return {
                "name": t.get("name"),
                "address": t.get("address", ""),
                "coordinates": [round(lng, 4), round(lat, 4)],
                "strategy": "官方输入提示自动补全"
            }

    # 3. 第三梯队：不带 types 的 POI 搜索
    d3 = run_cmd("poi_search", {"keywords": community_name, "city": city})
    pois3 = d3.get("pois", [])
    if pois3:
        p = pois3[0]
        lng, lat = map(float, p["location"].split(","))
        return {
            "name": p["name"],
            "address": p.get("address", ""),
            "coordinates": [round(lng, 4), round(lat, 4)],
            "strategy": "通用POI优先"
        }

    return None

if __name__ == "__main__":
    all_15 = [
        "盘古嘉德", "盘古天地", "佳兆业壹号", "保利湖畔阳光苑",
        "龙湖郦城", "中信泰富又一城", "华润中央公园", "绿地清猗园",
        "中冶祥腾城市广场", "恒盛豪庭", "嘉城", "水岸秀苑",
        "绿地天呈", "安亭新镇", "塔城新村"
    ]
    print(f"自动化漏斗算法测试全部 15 个小区：\n")
    for name in all_15:
        r = query_gaode_poi(name)
        if r:
            print(f"✅ {name:12} -> {r['name']:18} 坐标: {r['coordinates']} | 策略: {r['strategy']}")
        else:
            print(f"❌ {name:12} -> 失败")
