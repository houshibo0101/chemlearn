const { chromium } = require('playwright-core');

const URL = process.argv[2] || 'http://127.0.0.1:8123/chem/app/';
const OUT = process.argv[3] || 'D:/学习中心/部署工具/windows/shot_win.png';

(async () => {
  const browser = await chromium.launch({
    executablePath: 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',
    headless: true,
  });
  const page = await browser.newPage({ viewport: { width: 1500, height: 950 } });
  const errs = [];
  page.on('console', m => { if (m.type() === 'error') errs.push(m.text()); });
  page.on('pageerror', e => errs.push('PAGEERROR ' + e.message));

  await page.goto(URL, { waitUntil: 'networkidle', timeout: 45000 });
  await page.waitForTimeout(2500);

  const title = await page.title();
  const bodyLen = (await page.evaluate(() => document.body.innerText || '')).trim().length;
  const appHTML = await page.evaluate(() => (document.querySelector('#app') || {}).innerHTML || '');
  console.log('TITLE   :', title);
  console.log('APP_LEN :', appHTML.length);
  console.log('BODYLEN :', bodyLen);
  console.log('ERRORS  :', errs.length ? errs.slice(0, 5) : 'none');
  await page.screenshot({ path: OUT, fullPage: false });

  // 登录页交互测试
  try {
    const inputs = await page.locator('input:visible').count();
    console.log('INPUTS  :', inputs);
    if (inputs >= 2) {
      await page.locator('input:visible').nth(0).fill('admin');
      await page.locator('input:visible').nth(1).fill('admin123');
      await page.keyboard.press('Enter');
      await page.waitForTimeout(4000);
      const after = (await page.evaluate(() => document.body.innerText || '')).slice(0, 120).replace(/\s+/g, ' ');
      console.log('AFTER_LOGIN:', after);
      await page.screenshot({ path: OUT.replace('.png', '_in.png'), fullPage: false });
    }
  } catch (e) {
    console.log('LOGIN_ERR:', e.message.split('\n')[0]);
  }
  await browser.close();
})();
