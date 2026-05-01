from __future__ import annotations

import re
from urllib.parse import urlparse
from typing import Any

NODESEEK_CLIENT_HINT_HEADERS = {
    "sec-ch-ua",
    "sec-ch-ua-mobile",
    "sec-ch-ua-platform",
    "sec-ch-ua-full-version",
    "sec-ch-ua-full-version-list",
    "sec-ch-ua-arch",
    "sec-ch-ua-bitness",
    "sec-ch-ua-wow64",
    "sec-ch-ua-model",
    "sec-ch-ua-platform-version",
}

from playwright.async_api import async_playwright

from ..models import CheckinOutcome, SiteConfig
from .base import SiteAdapter


MOBILE_UA = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
)


class NodeSeekAdapter(SiteAdapter):
    site_type = "nodeseek"

    async def checkin(self, site: SiteConfig, *, headless: bool, mobile: bool, channel: str) -> CheckinOutcome:
        async with async_playwright() as p:
            browser_type = getattr(p, "chromium")
            browser = await browser_type.launch(
                headless=headless,
                channel=channel,
                chromium_sandbox=False,
            )
            context = await browser.new_context(
                is_mobile=mobile,
                has_touch=mobile,
                viewport={"width": 430, "height": 932} if mobile else {"width": 1365, "height": 900},
                user_agent=site.user_agent or (MOBILE_UA if mobile else None),
                locale="zh-CN",
                extra_http_headers={"Accept-Language": "zh-CN,zh;q=0.9"},
            )

            async def _strip_client_hints(route, request):
                if urlparse(request.url).hostname and urlparse(request.url).hostname.endswith("nodeseek.com"):
                    headers = {
                        key: value
                        for key, value in request.headers.items()
                        if key.lower() not in NODESEEK_CLIENT_HINT_HEADERS
                    }
                    await route.continue_(headers=headers)
                else:
                    await route.continue_()

            await context.route("**/*", _strip_client_hints)
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

            # Warm up the session on the homepage first, then enter the board.
            await page.goto("https://www.nodeseek.com/", wait_until="domcontentloaded", timeout=60000)
            await page.wait_for_load_state("load")
            await page.wait_for_timeout(1500)

            await page.goto(site.url, wait_until="domcontentloaded", timeout=60000)
            await page.wait_for_load_state("load")
            try:
                await page.wait_for_function(
                    """
                    () => {
                      const text = document.body?.innerText || '';
                      return text.includes('试试手气') || text.includes('今日签到获得鸡腿') || text.includes('今日还未签到');
                    }
                    """,
                    timeout=10000,
                )
            except Exception:
                pass

            body_text = await page.locator("body").inner_text()
            success, message = self._parse_message(body_text)
            if success and message != "签到请求已触发，但未能自动提取结果":
                await context.close()
                await browser.close()
                return self.outcome(site, True, message, body_text=body_text, url=page.url, already_signed=True)

            # The board page shows a sign-in button with the label "试试手气".
            sign_button = page.get_by_role("button", name="试试手气")
            if await sign_button.count():
                await sign_button.first.click()
            else:
                reward_button = page.get_by_role("button", name=re.compile(r"鸡腿 x\s*\d+"))
                if await reward_button.count():
                    return self.outcome(site, True, "今日已领取签到奖励", body_text=body_text, url=page.url, already_signed=True)
                raise RuntimeError("未找到 NodeSeek 签到按钮")

            # Click the sign-in button and inspect the attendance API response.
            async with page.expect_response(
                lambda response: "/api/attendance" in response.url,
                timeout=10000,
            ) as attendance_response_info:
                await sign_button.first.click()

            attendance_response = await attendance_response_info.value
            response_text = await attendance_response.text()

            if attendance_response.status == 403:
                await context.close()
                await browser.close()
                return self.outcome(
                    site,
                    False,
                    "签到接口返回 403，高风险操作，当前 cookie/浏览器上下文未通过校验",
                    body_text=body_text,
                    url=page.url,
                    response_status=attendance_response.status,
                    response_text=response_text,
                )

            await page.wait_for_timeout(3000)
            body_text = await page.locator("body").inner_text()
            success, message = self._parse_message(body_text)

            await context.close()
            await browser.close()
            return self.outcome(
                site,
                success,
                message,
                body_text=body_text,
                url=page.url,
                response_status=attendance_response.status,
                response_text=response_text,
            )

    @staticmethod
    def _parse_message(body_text: str) -> tuple[bool, str]:
        patterns = [
            (r"今天的签到收益是(\d+)个鸡腿", True),
            (r"今日签到获得鸡腿(\d+)个，当前排名第(\d+)", True),
            (r"今日还未签到", False),
            (r"high risk action", False),
        ]
        for pattern, success in patterns:
            match = re.search(pattern, body_text)
            if match:
                if "当前排名第" in pattern:
                    return True, f"签到成功，获得 {match.group(1)} 个鸡腿，当前排名第 {match.group(2)}"
                if "今天的签到收益" in pattern:
                    return True, f"签到成功，获得 {match.group(1)} 个鸡腿"
                if pattern == r"high risk action":
                    return False, "接口返回 high risk action，需要更接近真实浏览器的上下文或额外 cookie"
                return False, "页面仍显示未签到"
        return True, "签到请求已触发，但未能自动提取结果"
