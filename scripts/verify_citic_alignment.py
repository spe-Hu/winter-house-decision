import asyncio
from playwright.async_api import async_playwright
import os

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1440, "height": 900})
        
        # 访问本地 index.html
        url = "file://" + os.path.abspath("index.html")
        await page.goto(url)
        await page.wait_for_timeout(3000)
        
        # 让地图平移并缩放到嘉定新城站中信泰富核心区
        # 经纬度：121.2535, 31.3320，zoom 16
        await page.evaluate("""() => {
            if (window.map) {
                window.map.setView([31.3320, 121.2535], 16);
            }
        }""")
        
        # 等待切片和图钉加载
        await page.wait_for_timeout(3000)
        
        # 截图嘉定新城站中信泰富图钉与底图印刷文字重合情况
        os.makedirs("test_results", exist_ok=True)
        await page.screenshot(path="test_results/zhongxin_phase_perfect_alignment.png")
        print("✅ 嘉定新城站中信泰富图钉与底图对齐截图已保存: test_results/zhongxin_phase_perfect_alignment.png")
        
        # 点击三期图钉打开抽屉查看
        await page.evaluate("""() => {
            const target = window.COMMUNITY_DATA.find(c => c.name.includes('中信泰富又一城三期'));
            if (target && typeof openDrawer === 'function') {
                openDrawer(target);
            }
        }""")
        await page.wait_for_timeout(1500)
        await page.screenshot(path="test_results/zhongxin_phase3_drawer_aligned.png")
        print("✅ 中信泰富三期抽屉详情截图已保存: test_results/zhongxin_phase3_drawer_aligned.png")

        # 切换为卫星实景图再次截图
        await page.evaluate("""() => {
            if (window.map) {
                // 关闭抽屉
                if (typeof closeDrawer === 'function') closeDrawer();
                // 切换到底图控制器
                const inputs = document.querySelectorAll('.leaflet-control-layers-selector');
                if (inputs.length > 1) {
                    inputs[1].click(); // 切换卫星图
                }
            }
        }""")
        await page.wait_for_timeout(2500)
        await page.screenshot(path="test_results/zhongxin_satellite_perfect_alignment.png")
        print("✅ 中信泰富卫星实景对齐截图已保存: test_results/zhongxin_satellite_perfect_alignment.png")
        
        await browser.close()

asyncio.run(main())
