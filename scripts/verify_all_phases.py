import sys
import json
import subprocess
import math

GAODE_SKILL_SCRIPT = "/Users/wentao.hu/.workbuddy/skills/gaode-map-pro__skillhub/scripts/main.py"

def query_gaode_poi_raw(name, city="上海"):
    cmd = [sys.executable, GAODE_SKILL_SCRIPT, "poi_search", json.dumps({"keywords": name, "city": city}, ensure_ascii=False)]
    res = subprocess.run(cmd, capture_output=True, text=True)
    try:
        data = json.loads(res.stdout).get("data", {})
        pois = data.get("pois", [])
        if pois:
            p = pois[0]
            lng, lat = map(float, p["location"].split(","))
            return {
                "name": p["name"],
                "address": p.get("address", ""),
                "coordinates": [round(lng, 4), round(lat, 4)]
            }
    except Exception as e:
        pass
    return None

def calc_dist(c1, c2):
    # 简易欧式转米 (1度约111km, 纬度31度经度1度约95km)
    dx = (c1[0] - c2[0]) * 95000
    dy = (c1[1] - c2[1]) * 111000
    return round(math.sqrt(dx*dx + dy*dy))

# 读取 data/jiading_xiaoqu.json 中的全量小区列表
with open("data/jiading_xiaoqu.json", "r", encoding="utf-8") as f:
    COMMUNITIES = json.load(f)

print(f"正在校验 data/jiading_xiaoqu.json 中的 {len(COMMUNITIES)} 个小区与高德官方严格POI的对齐情况...")
for c in COMMUNITIES:
    name = c["name"]
    curr_coords = c["coordinates"]
    gaode_res = query_gaode_poi_raw(name)
    if gaode_res:
        g_coords = gaode_res["coordinates"]
        dist = calc_dist(curr_coords, g_coords)
        flag = "🔴 [偏差过大!]" if dist > 300 else "🟢 [精准]"
        print(f"{flag} {name}: 当前={curr_coords}, 高德={g_coords}, 距离差={dist}米 | 高德地址={gaode_res['address']}")
    else:
        print(f"⚪ {name}: 高德未直接搜出POI, 当前={curr_coords}")
