from playwright.sync_api import sync_playwright
import pathlib
root=pathlib.Path(r'D:\git\temp\contract-check')
with sync_playwright() as p:
    b=p.chromium.launch()
    pg=b.new_page(viewport={'width':1400,'height':900},device_scale_factor=2)
    pg.goto((root/'docs/architecture.html').as_uri()); pg.wait_for_timeout(800)
    s=pg.query_selector('svg').bounding_box()
    lg=pg.evaluate("""(()=>{const w=document.createTreeWalker(document.body,NodeFilter.SHOW_TEXT);let n;while(n=w.nextNode()){if(n.textContent.includes('本次已實作')){const r=n.parentElement.closest('div,p,section')||n.parentElement;const b=r.getBoundingClientRect();return [b.x,b.y,b.width,b.height]}}})()""")
    print(s,lg)
    y0=min(s['y'],lg[1])-8; x0=min(s['x'],lg[0])-8
    x1=max(s['x']+s['width'],lg[0]+lg[2])+8; y1=s['y']+s['height']+8
    pg.screenshot(path='img/arch.png',clip={'x':x0,'y':y0,'width':x1-x0,'height':y1-y0},full_page=True)
    b.close()
