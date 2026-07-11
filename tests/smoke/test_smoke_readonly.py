import datetime as dt
import os
import sys
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

BASE_URL = os.environ.get("SMOKE_BASE_URL", "https://10.0.0.16").rstrip("/")
BROWSER_EXE = os.environ.get("SMOKE_BROWSER", "/usr/bin/google-chrome")
SCREENSHOT_DIR = Path(os.environ.get("SMOKE_SCREENSHOT_DIR", "output/smoke-screenshots"))

ROLES = [
    {
        "name": "member",
        "username": os.environ.get("SMOKE_MEMBER_USER", "smoke_member"),
        "password": os.environ.get("SMOKE_MEMBER_PASS", ""),
        "expected_text": "个人",
    },
    {
        "name": "buddy",
        "username": os.environ.get("SMOKE_BUDDY_USER", "smoke_buddy"),
        "password": os.environ.get("SMOKE_BUDDY_PASS", ""),
        "expected_text": "Buddy",
    },
    {
        "name": "leader",
        "username": os.environ.get("SMOKE_LEADER_USER", "smoke_leader"),
        "password": os.environ.get("SMOKE_LEADER_PASS", ""),
        "expected_text": "Leader",
    },
]


def _screenshot_path(role: str, suffix: str) -> Path:
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    return SCREENSHOT_DIR / f"{role}_{suffix}_{timestamp}.png"


def _check_role(role: dict) -> None:
    assert role["password"], f"SMOKE_{role['name'].upper()}_PASS is not set"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, executable_path=BROWSER_EXE)
        context = browser.new_context(ignore_https_errors=True)
        page = context.new_page()

        try:
            # 1. Login page loads
            page.goto(f"{BASE_URL}/accounts/login/", wait_until="networkidle")
            expect(page.locator("input[name='username']")).to_be_visible()
            expect(page.locator("input[name='password']")).to_be_visible()

            # 2. Submit credentials
            page.fill("input[name='username']", role["username"])
            page.fill("input[name='password']", role["password"])
            page.click("button[type='submit']")
            page.wait_for_load_state("networkidle")

            # 3. Should be redirected away from login
            assert "/accounts/login/" not in page.url, (
                f"{role['name']} login failed, still on {page.url}"
            )

            # 4. Dashboard has role-specific navigation
            page.wait_for_selector("main", timeout=5000)
            assert page.locator("main").count() == 1, "page has no single <main> landmark"
            body_text = page.locator("body").inner_text()
            assert role["expected_text"] in body_text, (
                f"{role['name']} dashboard missing '{role['expected_text']}'"
            )

            # 5. No server error page
            assert "Server Error" not in page.title(), (
                f"{role['name']} hit server error page"
            )

            # Success screenshot
            page.screenshot(path=_screenshot_path(role["name"], "ok"))

        except Exception:
            # Failure screenshot
            try:
                page.screenshot(path=_screenshot_path(role["name"], "fail"))
            except Exception:
                pass
            raise
        finally:
            browser.close()


def test_smoke_member_login_dashboard():
    _check_role(ROLES[0])


def test_smoke_buddy_login_dashboard():
    _check_role(ROLES[1])


def test_smoke_leader_login_dashboard():
    _check_role(ROLES[2])


if __name__ == "__main__":
    # Allow running without pytest for quick manual checks
    failures = 0
    for role in ROLES:
        try:
            _check_role(role)
            print(f"OK: {role['name']}")
        except Exception as exc:
            print(f"FAIL: {role['name']} - {exc}")
            failures += 1
    sys.exit(1 if failures else 0)
