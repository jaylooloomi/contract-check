from playwright.sync_api import sync_playwright
import pathlib
root=pathlib.Path(r'D:\git\temp\contract-check')
with sync_playwright() as p:
    b=p.chromium.launch()
    pg=b.new_page(viewport={'width':1400,'height':900},device_scale_factor=2)
    pg.goto((root/'docs/architecture.html').as_uri()); pg.wait_for_timeout(800)
    svgs=pg.query_selector_all('svg'); print('svgs',len(svgs))
    print(pg.evaluate("document.body.innerText.slice(0,600)"))
    pg.screenshot(path='img/arch_full.png',full_page=True)
    for url in ['http://localhost:8000/?id=11','http://localhost:8000/']:
        try:
            pg.goto(url,timeout=15000); pg.wait_for_timeout(2500)
            pg.screenshot(path='img/app.png'); print('app ok',url); break
        except Exception as e: print('fail',url,e)
    b.close()
