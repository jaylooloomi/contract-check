from playwright.sync_api import sync_playwright
from PIL import Image
with sync_playwright() as p:
    b=p.chromium.launch(); pg=b.new_page(viewport={'width':1400,'height':800},device_scale_factor=2)
    pg.goto('http://localhost:8000/?id=11'); pg.wait_for_timeout(1500)
    if pg.is_hidden('#result'):
        pg.evaluate("load(11)"); pg.wait_for_timeout(2000)
    pg.screenshot(path='img/app.png'); b.close()
Image.open('img/arch.png').crop((0,0,2110,1160)).save('img/arch.png')
