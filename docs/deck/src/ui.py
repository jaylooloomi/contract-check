from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b=p.chromium.launch(); pg=b.new_page(viewport={'width':1280,'height':800},device_scale_factor=2)
    for n,u in [('a','/?id=11'),('b','/v/b?id=11'),('c','/v/c?id=11')]:
        pg.goto('http://localhost:8000'+u); pg.wait_for_timeout(2500)
        pg.screenshot(path=f'img/ui_{n}.png')
    b.close()
