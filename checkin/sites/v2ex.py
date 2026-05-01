from __future__ import annotations

import re
from urllib.parse import urlparse

from playwright.async_api import async_playwright

from ..models import CheckinOutcome, SiteConfig
from .base import SiteAdapter


SAFARI_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.6 Safari/605.1.15"
)


class V2EXAdapter(SiteAdapter):
    site_type = "v2ex"

    async def checkin(self, site: SiteConfig, *, headless: bool, mobile: bool, channel: str) -> CheckinOutcome:
        async with async_playwright() as p:
            browser_type = getattr(p, "chromium")
            browser = await browser_type.launch(
                headless=headless,
                channel=channel,
                chromium_sandbox=False,
            )
            context = await browser.new_context(
                is_mobile=False,
                has_touch=False,
                viewport={"width": 1365, "height": 900},
                user_agent=site.user_agent or SAFARI_UA,
                locale="zh-CN",
                extra_http_headers={"Accept-Language": "zh-CN,zh;q=0.9"},
            )
            if site.cookies:
                parsed = urlparse(site.url)
                cookie_url = f"{parsed.scheme}://{parsed.netloc}"
                await context.add_cookies(
                    [
                        {
                            "name": name,
                            "value": value,
                            "url": cookie_url,
                        }
                        for name, value in site.cookies.items()
                    ]
                )

            page = await context.new_page()
            page.set_default_timeout(60000)
            await page.goto(site.url, wait_until="domcontentloaded", timeout=60000)
            await page.wait_for_load_state("load")

            # The home page exposes the reward entry point as "领取今日的登录奖励".
            entry = page.locator("text=领取今日的登录奖励")
            if await entry.count():
                await entry.first.click()
                await page.wait_for_load_state("networkidle")

            if "/mission/daily" not in page.url:
                await page.goto(f"{site.url.rstrip('/')}/mission/daily", wait_until="networkidle")

            body_text = await page.locator("body").inner_text()
            success, message = self._parse_message(body_text)
            if success:
                await context.close()
                await browser.close()
                return self.outcome(site, True, message, body_text=body_text, url=page.url, already_signed="已领取" in message)

            reward_button = page.get_by_role("button", name=re.compile(r"领取.*铜币"))
            await reward_button.click()
            await page.wait_for_load_state("networkidle")

            body_text = await page.locator("body").inner_text()
            success, message = self._parse_message(body_text)

            await context.close()
            await browser.close()
            return self.outcome(site, success, message, body_text=body_text, url=page.url)

    @staticmethod
    def _parse_message(body_text: str) -> tuple[bool, str]:
        patterns = [
            (r"已成功领取每日登录奖励\s*(\d+)\s*铜币", True),
            (r"今日登录奖励已领取", True),
            (r"每日登录奖励已领取", True),
            (r"领取今日的登录奖励", True),
        ]
        for pattern, success in patterns:
            match = re.search(pattern, body_text)
            if match:
                if match.lastindex:
                    return True, f"签到成功，获得 {match.group(1)} 铜币"
                if "已领取" in pattern:
                    return True, "今日已领取登录奖励"
                return True, "找到登录奖励入口"
        return False, "未能识别 V2EX 登录奖励页面"
