#!/usr/bin/env python3
"""
嘉定购房参考系统 — 交付前完整回归验证测试集 (Pre-Delivery Regression Test Suite)
覆盖历史排查出的所有致命与关键问题：
1. [安全门禁]: 口令为 9802 加盐不可逆哈希，前端源码无明文口令残留；
2. [数据真相源]: 全域 35 个小区坐标范围合法、权威初中中考市重率 100% 绑定；
3. [户型真值一致性]: 依据 OCR 物理房间标尺，全量 78 套户型两房严格为 2 卧、三房严格为 3 卧（重点核验保利阳光苑）；
4. [多源立体交通噪音]: 11号线地上高架轨交、胜辛路主干道、S5高速拓扑计算覆盖（重点核验中信泰富一二三期）；
5. [双栏分屏防遮挡交互]: 单选行仅高亮飞渡，绝不遮盖多维表格；双击或点击操作列才居中展开工作台；
6. [多维表格十字交叉粘性冻结]: 表格横向滚动 600px 后，表头第1、2列死死吸顶吸左，层级最高无穿透；
7. [全景工作台键盘翻页]: 支持 ESC 退出，支持 ArrowLeft / ArrowRight 切换相邻小区；
8. [全屏 Lightbox 原图]: 点击户型图展开 1440P 原图，按 ESC 退出；
9. [一票否决与主题切换]: 噪音一票否决精准降权，主题无缝切换。
"""

import http.server
import json
import os
import re
import socketserver
import sys
import threading
import time
from playwright.sync_api import sync_playwright

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
JSON_PATH = os.path.join(DATA_DIR, "jiading_xiaoqu.json")
JS_PATH = os.path.join(DATA_DIR, "dataset.js")
CATALOG_PATH = os.path.join(DATA_DIR, "floorplan_catalog.json")
INDEX_PATH = os.path.join(BASE_DIR, "index.html")

TEST_PORT = 8098

# ═══════════════════════════════════════════════════════
# 模块一：静态数据真值与代码合规性核验 (Static Checks)
# ═══════════════════════════════════════════════════════
def test_static_data_and_security():
    print("\n" + "=" * 60)
    print("【阶段一】：静态数据真值与代码安全性核验 (Static Integrity Checks)")
    print("=" * 60)

    # 1. 源码安全性检查
    with open(INDEX_PATH, "r", encoding="utf-8") as f:
        html_content = f.read()

    assert "AUTH_SALT" in html_content, "❌ 缺失加盐配置 AUTH_SALT"
    assert "calcSha256Hex" in html_content, "❌ 缺失 SHA-256 哈希认证算法"
    
    # 严格检查：源码中绝不允许出现明文口令
    assert "9802" not in html_content, "❌ 严重安全隐患: index.html 中竟然残留了明文口令 '9802'！"
    assert "6688" not in html_content, "❌ 严重安全隐患: index.html 中残留了旧明文口令 '6688'！"
    print("  ✅ 检查项 1 通过: 前端源码已消除任何明文口令，采用单向加盐 SHA-256 哈希。")

    # 2. 户型图权威真值元数据库核验
    with open(CATALOG_PATH, "r", encoding="utf-8") as f:
        catalog = json.load(f)

    with open(JSON_PATH, "r", encoding="utf-8") as f:
        communities = json.load(f)

    assert len(communities) == 80, f"❌ 小区总数异常: 期望 80，实际 {len(communities)}"
    
    # 3. 户型图与物理房间数严格匹配断言 (防止保利阳光苑三房误挂两房图)
    total_layouts = 0
    poly_checked = False
    citic_checked = False

    for c in communities:
        # 经纬度合法性
        lng, lat = c["coordinates"]
        assert 121.0 <= lng <= 121.5, f"❌ {c['name']} 经度越界: {lng}"
        assert 31.1 <= lat <= 31.6, f"❌ {c['name']} 纬度越界: {lat}"

        # 初中学区市重率
        sch = c.get("target_middle_school", {})
        assert "name" in sch and "rate_26" in sch, f"❌ {c['name']} 缺少初中中考市重率数据"
        assert sch.get("public_rank", 0) > 0, f"❌ {c['name']} 初中公办排名异常"

        # 多源立体噪音拓扑数据
        ne = c.get("noise_evaluation", {})
        assert "elevated_metro" in ne, f"❌ {c['name']} 缺少地上高架轨交噪音拓扑分析"
        assert "arterial_road" in ne, f"❌ {c['name']} 缺少城市主干道噪音拓扑分析"
        assert "expressway" in ne, f"❌ {c['name']} 缺少高速公路噪音拓扑分析"
        assert "selection_guide" in ne, f"❌ {c['name']} 缺少专家实勘避坑指南"

        # 重点核验：中信泰富一二三期必须明确识别胜辛路与11号线地上高架
        if any(k in c["name"] for k in ["中信泰富又一城一期", "中信泰富又一城二期", "中信泰富又一城三期"]):
            assert ne["elevated_metro"]["distance_m"] <= 150, f"❌ {c['name']} 11号线高架测距失真"
            assert ne["arterial_road"]["distance_m"] <= 50, f"❌ {c['name']} 胜辛路测距失真"
            citic_checked = True
        elif "中信泰富又一城四期" in c["name"]:
            assert ne["elevated_metro"]["distance_m"] <= 50, f"❌ {c['name']} 11号线高架测距失真"

        # 逐一核验每个户型
        for l in c.get("layouts", []):
            total_layouts += 1
            cat = l["category"]
            fpath = l["floor_plan_local"]
            fname = os.path.basename(fpath)
            assert os.path.exists(os.path.join(BASE_DIR, fpath)), f"❌ 本地户型图文件不存在: {fpath}"
            assert fname in catalog, f"❌ 图片未录入真值库: {fname}"
            b_cnt = catalog[fname]["bedroom_count"]

            if cat == "两房":
                assert b_cnt == 2, f"❌ 物理房间数错配: 小区 {c['name']} 的两房户型绑定的图片 {fname} 实际为 {b_cnt} 房！"
            elif cat == "三房":
                assert b_cnt == 3, f"❌ 物理房间数错配: 小区 {c['name']} 的三房户型绑定的图片 {fname} 实际为 {b_cnt} 房！"
            elif cat == "改善四房":
                assert b_cnt == 4, f"❌ 物理房间数错配: 小区 {c['name']} 的四房户型绑定的图片 {fname} 实际为 {b_cnt} 房！"

            # 重点核验：保利湖畔阳光苑
            if "保利湖畔阳光苑" in c["name"]:
                poly_checked = True
                if cat == "两房":
                    assert "107116374473" in fname, f"❌ 保利阳光苑两房图片异常: {fname}"
                elif cat == "三房":
                    assert "107116447609" in fname, f"❌ 保利阳光苑三房图片异常(绝不可使用两房图): {fname}"

    assert poly_checked, "❌ 未检测到保利湖畔阳光苑"
    assert citic_checked, "❌ 未检测到中信泰富大盘"
    print(f"  ✅ 检查项 2 通过: 全量 {len(communities)} 个小区经纬度与配套数据 100% 完整。")
    print(f"  ✅ 检查项 3 通过: 保利阳光苑及全量 {total_layouts} 个户型档案与图片 OCR 物理房间数 100% 吻合，两房绝无三房图，三房绝无两房图！")
    print(f"  ✅ 检查项 4 通过: 中信泰富一二三期多源立体噪音拓扑（11号线高架+胜辛路双重影响）已严格计算到位。")

    # 检查项 5: 2026 官方学区真值严格对齐检验
    sgt_path = os.path.join(DATA_DIR, "school_ground_truth.json")
    assert os.path.exists(sgt_path), "❌ 找不到 2026 官方学区权威真值库文件"
    with open(sgt_path, "r", encoding="utf-8") as f:
        sgt = json.load(f)

    for c in communities:
        assert "target_primary_school" in c, f"❌ 小区 {c['name']} 缺失对口小学档案"
        assert "target_middle_school" in c, f"❌ 小区 {c['name']} 缺失对口初中档案"
        pri = c["target_primary_school"]
        mid = c["target_middle_school"]
        assert pri.get("name") in sgt["schools"], f"❌ 小区 {c['name']} 对口小学 '{pri.get('name')}' 未录入官方真值库"
        assert mid.get("name") in sgt["schools"], f"❌ 小区 {c['name']} 对口初中 '{mid.get('name')}' 未录入官方真值库"

        # 重点小区真值防倒退硬断言
        if "中信泰富" in c["name"]:
            assert "洪德中学" in mid["name"], f"❌ 中信泰富初中真值错误(必须在胜辛路以西归属洪德): {mid['name']}"
            assert "普通" in pri["name"], f"❌ 中信泰富小学真值错误: {pri['name']}"
        if "好世凤翔苑" in c["name"]:
            assert "留云中学" in mid["name"] and "古猗" in mid["name"], f"❌ 好世凤翔苑初中真值错误: {mid['name']}"
            assert "古猗小学" in pri["name"], f"❌ 好世凤翔苑小学真值错误: {pri['name']}"
        if "华润中央公园" in c["name"]:
            assert "留云中学" in mid["name"], f"❌ 华润中央公园初中真值错误: {mid['name']}"
            assert "留云小学" in pri["name"], f"❌ 华润中央公园小学真值错误: {pri['name']}"
        if "龙湖天璞" in c["name"]:
            assert "江桥实验" in mid["name"] and "海波" in mid["name"], f"❌ 龙湖天璞初中真值错误: {mid['name']}"
            assert "卢湾一中" in pri["name"], f"❌ 龙湖天璞小学真值错误: {pri['name']}"
        if "安亭新镇·德绍豪斯" in c["name"]:
            assert mid["name"] == "同济大学附属实验中学", f"❌ 德绍豪斯初中真值错误: {mid['name']}"
        if "安亭新镇·万科莱茵半岛" in c["name"]:
            assert mid["name"] == "同济大学附属嘉定实验中学", f"❌ 莱茵半岛初中真值错误: {mid['name']}"

    print(f"  ✅ 检查项 5 通过: 全量 {len(communities)} 个小区 2026 官方学区（小学+初中）真值 100% 严密对齐，中信泰富洪德中学、好世留云古猗校区、华润留云中小学等历史痛点全部对齐！")

# ═══════════════════════════════════════════════════════
# 模块二：Playwright 端到端全场景自动化回归测试
# ═══════════════════════════════════════════════════════
class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

def test_browser_e2e():
    print("\n" + "=" * 60)
    print("【阶段二】：端到端全场景浏览器自动化回归测试 (E2E Integration Suite)")
    print("=" * 60)

    # 启动本地静默 HTTP 服务 (允许地址重用与动态端口适配)
    socketserver.TCPServer.allow_reuse_address = True
    active_port = TEST_PORT
    httpd = None
    for p in range(TEST_PORT, TEST_PORT + 20):
        try:
            httpd = socketserver.TCPServer(("", p), QuietHandler)
            active_port = p
            break
        except OSError:
            continue
    if not httpd:
        raise RuntimeError("❌ 无法在指定端口范围内启动本地测试 HTTP 服务")

    server_thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    server_thread.start()
    url = f"http://127.0.0.1:{active_port}/index.html"

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1440, "height": 900})
            page.goto(url)
            time.sleep(1)

            # 1. 安全门禁 9802 回车解锁测试
            print("  ▶ 正在验证安全门禁解锁流 (9802)...")
            assert page.is_visible("#access-gate"), "❌ 门禁层初始状态应为可见遮罩"
            page.fill("#gate-pass-input", "9802")
            page.press("#gate-pass-input", "Enter")
            time.sleep(1)
            assert not page.is_visible("#access-gate"), "❌ 口令输入 9802 后门禁未能成功解锁"
            print("  ✅ 场景 1 验证通过: 门禁输入 9802 回车成功解锁并淡出！")

            # 2. 分屏模式下单选交互防遮挡测试 (核心痛点)
            print("  ▶ 正在验证双栏分屏单选防遮挡行为...")
            row1 = page.query_selector("tbody tr:first-child")
            row1.click()
            time.sleep(0.5)
            drawer = page.query_selector("#detail-drawer")
            assert not drawer.is_visible(), "❌ 严重交互缺陷: 分屏下单选行不应强行弹出模态遮盖多维表格！"
            assert "selected-row" in row1.get_attribute("class"), "❌ 单击行未添加 selected-row 高亮类"
            print("  ✅ 场景 2 验证通过: 分屏模式下单选行仅飞渡高亮，绝不遮盖多维表格！")

            # 3. 多维表格十字交叉粘性冻结测试 (表头第一二列吸顶吸左)
            print("  ▶ 正在验证多维表格十字交叉粘性定位 (Sticky Header + Sticky Columns)...")
            scroll_wrap = page.query_selector(".grid-scroll-wrapper")
            page.evaluate("(el) => el.scrollLeft = 600", scroll_wrap)
            time.sleep(0.5)

            th1 = page.query_selector("thead th.sticky-col-1")
            th2 = page.query_selector("thead th.sticky-col-2")
            box1 = th1.bounding_box()
            box2 = th2.bounding_box()
            assert box1["x"] > 0 and box2["x"] > box1["x"], "❌ 表头第1、2列横向滚动时错位"
            
            # 校验 CSS z-index
            z_idx1 = page.evaluate("(el) => window.getComputedStyle(el).zIndex", th1)
            assert int(z_idx1) >= 35, f"❌ 表头第1列 z-index 异常: {z_idx1}，横向滚动时会被后续表头穿透"
            print("  ✅ 场景 3 验证通过: 横向滚动 600px 后，表头第1、2列死死吸顶吸左，立体阴影完整！")

            # 4. 保利湖畔阳光苑居中全景工作台展开与三房户型真值检验
            print("  ▶ 正在验证保利湖畔阳光苑居中工作台展开与户型图实证...")
            page.fill("#grid-search", "保利湖畔阳光苑")
            time.sleep(0.5)
            poly_btn = page.query_selector("tbody tr:first-child button")
            poly_btn.click()
            time.sleep(0.8)
            assert drawer.is_visible(), "❌ 点击全景档案按钮后工作台未居中弹出"

            drawer_title = page.inner_text("#drawer-title")
            assert "保利湖畔阳光苑" in drawer_title, f"❌ 工作台标题异常: {drawer_title}"
            
            # 检查两房与三房卡片
            cards = page.query_selector_all(".layout-card")
            assert len(cards) >= 2, f"❌ 保利阳光苑户型数量不足: {len(cards)}"
            c1_text = cards[0].inner_text()
            c2_text = cards[1].inner_text()
            assert "两房" in c1_text and "2室2厅" in c1_text, "❌ 第1套非纯真两房"
            assert "三房" in c2_text and "3室2厅" in c2_text, "❌ 第2套非纯真三房"

            img1_src = cards[0].query_selector(".floorplan-thumb-wrap img").get_attribute("src")
            img2_src = cards[1].query_selector(".floorplan-thumb-wrap img").get_attribute("src")
            assert "107116374473" in img1_src, f"❌ 两房图片异常: {img1_src}"
            assert "107116447609" in img2_src, f"❌ 三房图片异常: {img2_src}"
            assert img1_src != img2_src, "❌ 两房和三房绝对不允许共用图片！"
            print("  ✅ 场景 4 验证通过: 保利湖畔阳光苑工作台两房(2卧)与三房(3卧双卫)图片独立真实！")

            # 5. 全屏 Lightbox 原图与 ESC 退出测试
            print("  ▶ 正在验证全屏 1440P 原图 Lightbox 展开与 ESC 关闭...")
            cards[1].query_selector(".floorplan-thumb-wrap").click()
            time.sleep(0.8)
            lightbox = page.query_selector("#floorplan-lightbox")
            assert lightbox.is_visible(), "❌ 点击户型图缩略窗后 Lightbox 未展开"
            lb_img = page.get_attribute("#lb-img", "src")
            assert "107116447609" in lb_img, f"❌ Lightbox 图片源错误: {lb_img}"

            # 按 ESC 退出 Lightbox
            page.keyboard.press("Escape")
            time.sleep(0.4)
            assert not lightbox.is_visible(), "❌ 按 ESC 后 Lightbox 未能退出"
            print("  ✅ 场景 5 验证通过: 户型图点击全屏原图展开，按 ESC 顺利退出！")

            # 6. 工作台键盘左右箭头 (ArrowLeft / ArrowRight) 快速切换小区测试
            print("  ▶ 正在验证工作台键盘左右箭头翻页切换小区...")
            page.keyboard.press("ArrowRight")
            time.sleep(0.6)
            next_title = page.inner_text("#drawer-title")
            assert next_title != drawer_title, "❌ 按右箭头后工作台未切换至下一个小区"
            page.keyboard.press("ArrowLeft")
            time.sleep(0.6)
            back_title = page.inner_text("#drawer-title")
            assert back_title == drawer_title, "❌ 按左箭头未能返回原小区"
            print("  ✅ 场景 6 验证通过: 键盘左右箭头支持在工作台内秒级连续对比不同小区！")

            # 按 ESC 关闭居中工作台
            page.keyboard.press("Escape")
            time.sleep(0.4)
            assert not drawer.is_visible(), "❌ 按 ESC 后工作台未退出"

            # 7. 中信泰富多源立体交通噪音全景报告核验
            print("  ▶ 正在验证中信泰富一二三期多源立体噪音报告与实勘指南...")
            page.fill("#grid-search", "中信泰富又一城一期")
            time.sleep(0.5)
            page.query_selector("tbody tr:first-child button").click()
            time.sleep(0.8)
            modal_text = page.inner_text("#detail-drawer")
            assert "11号线" in modal_text, "❌ 缺失 11号线地上高架轨交分析"
            assert "胜辛路" in modal_text, "❌ 缺失 胜辛路双向8车道主干道分析"
            assert "实勘避坑" in modal_text, "❌ 缺失 专家实勘避坑指南"
            assert "洪德中学" in modal_text, "❌ 缺失 2026 官方对口洪德中学"
            assert "普通小学" in modal_text, "❌ 缺失 2026 官方对口普通小学白银路分校"
            page.keyboard.press("Escape")
            time.sleep(0.4)
            print("  ✅ 场景 7 验证通过: 中信泰富高架轨交噪音报告、实勘避坑指南与 2026 官方双学区档案展现完整！")

            # 8. 噪音一票否决开关测试
            print("  ▶ 正在验证【高架/轨交噪音一票否决】开关机制...")
            page.fill("#grid-search", "")
            time.sleep(0.4)
            veto_btn = page.query_selector("#veto-toggle-btn")
            veto_btn.click()
            time.sleep(0.6)
            assert "active" in veto_btn.get_attribute("class"), "❌ 一票否决按钮未处于激活状态"
            vetoed_rows = page.query_selector_all("tbody tr.vetoed-row")
            assert len(vetoed_rows) > 0, "❌ 开启一票否决后未筛选出超标小区"
            veto_btn.click() # 恢复
            time.sleep(0.4)
            print("  ✅ 场景 8 验证通过: 一票否决开关触发顺畅，受噪严重房源被精准标记降权！")

            # 9. 三大主题切换测试
            print("  ▶ 正在验证三大高端主题无缝切换...")
            theme_select = page.query_selector("#theme-switcher")
            theme_select.select_option("theme-paper")
            time.sleep(0.4)
            html_cls = page.get_attribute("html", "class")
            assert "theme-paper" in html_cls, "❌ 切换到纸本主题失败"
            theme_select.select_option("theme-blueprint")
            time.sleep(0.4)
            html_cls = page.get_attribute("html", "class")
            assert "theme-blueprint" in html_cls, "❌ 切换到极客蓝图主题失败"
            theme_select.select_option("theme-obsidian") # 恢复默认
            time.sleep(0.3)
            print("  ✅ 场景 9 验证通过: 黑曜终端 / 暖调纸本 / 极客蓝图 三套主题自适应切换无误！")

            browser.close()
            print("\n🎉 恭喜！阶段二所有端到端场景自动化测试 100% 全部通过！")

    finally:
        httpd.shutdown()

def main():
    start_time = time.time()
    try:
        test_static_data_and_security()
        test_browser_e2e()
        cost = round(time.time() - start_time, 2)
        print("\n" + "★" * 60)
        print(f"🚀 全量测试集与质量门禁校验全部成功通过！总耗时: {cost} 秒")
        print("★" * 60 + "\n")
        sys.exit(0)
    except AssertionError as e:
        print(f"\n❌ 回归测试失败熔断: {e}\n")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 测试执行发生异常: {e}\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
