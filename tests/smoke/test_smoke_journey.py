import datetime as dt
import json
import os
import re
import sys
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

BASE_URL = os.environ.get("SMOKE_BASE_URL", "https://10.0.0.16").rstrip("/")
BROWSER_EXE = os.environ.get("SMOKE_BROWSER", "/usr/bin/google-chrome")
SCREENSHOT_DIR = Path(
    os.environ.get("JOURNEY_SCREENSHOT_DIR", "output/journey-screenshots")
)

MEMBER_USER = os.environ.get("SMOKE_MEMBER_USER", "smoke_member")
MEMBER_PASS = os.environ.get("SMOKE_MEMBER_PASS", "")
BUDDY_USER = os.environ.get("SMOKE_BUDDY_USER", "smoke_buddy")
BUDDY_PASS = os.environ.get("SMOKE_BUDDY_PASS", "")
LEADER_USER = os.environ.get("SMOKE_LEADER_USER", "smoke_leader")
LEADER_PASS = os.environ.get("SMOKE_LEADER_PASS", "")

JOURNEY_YEAR = 3000
CYCLE_NAME = f"{JOURNEY_YEAR} 年度学习周期"


def _screenshot(page, name: str) -> None:
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    path = SCREENSHOT_DIR / f"journey_{name}_{timestamp}.png"
    page.screenshot(path=str(path))


def _login(page, username: str, password: str) -> None:
    page.goto(f"{BASE_URL}/accounts/login/", wait_until="networkidle")
    page.fill("input[name='username']", username)
    page.fill("input[name='password']", password)
    page.click("button[type='submit']")
    page.wait_for_load_state("networkidle")
    assert "/accounts/login/" not in page.url, f"login failed for {username}: {page.url}"


def _csrf(page) -> str:
    return page.locator("input[name='csrfmiddlewaretoken']").input_value()


def _post(page, url: str, data=None):
    headers = {
        "X-CSRFToken": _csrf(page),
        "Referer": BASE_URL,
    }
    return page.request.post(url, form=data or {}, headers=headers)


def _extract_id_from_url(url: str, prefix: str) -> int:
    match = re.search(re.escape(prefix) + r"(\d+)", url)
    assert match, f"could not extract id from {url} with prefix {prefix}"
    return int(match.group(1))


def _accept_dialogs(page):
    page.on("dialog", lambda dialog: dialog.accept())


def run_journey():
    assert MEMBER_PASS and BUDDY_PASS and LEADER_PASS, "smoke credentials are required"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, executable_path=BROWSER_EXE)

        # 1. Leader creates a far-future calendar cycle for the smoke member.
        leader_context = browser.new_context(ignore_https_errors=True)
        leader_page = leader_context.new_page()
        _accept_dialogs(leader_page)
        _login(leader_page, LEADER_USER, LEADER_PASS)

        leader_page.goto(f"{BASE_URL}/learning/cycles/", wait_until="networkidle")
        leader_page.fill("input[name='year']", str(JOURNEY_YEAR))
        leader_page.locator('label:has-text("smoke_member") input[type="checkbox"]').check()
        leader_page.click("button[type='submit']")
        leader_page.wait_for_load_state("networkidle")
        assert CYCLE_NAME in leader_page.content(), "newly created cycle not listed"
        _screenshot(leader_page, "01_leader_create_cycle")

        # 2. Get the cycle id via Django admin.
        leader_page.goto(f"{BASE_URL}/admin/learning/learningcycle/", wait_until="networkidle")
        leader_page.locator(f"a:has-text('{CYCLE_NAME}')").first.click()
        leader_page.wait_for_load_state("networkidle")
        cycle_id = _extract_id_from_url(leader_page.url, "/admin/learning/learningcycle/")
        leader_context.close()

        # 3. Member fills assessments and marks items as included.
        member_context = browser.new_context(ignore_https_errors=True)
        member_page = member_context.new_page()
        _accept_dialogs(member_page)
        _login(member_page, MEMBER_USER, MEMBER_PASS)

        member_page.goto(f"{BASE_URL}/learning/assessment/", wait_until="networkidle")
        rows = member_page.locator("tr.capability-row").all()
        assert rows, "no assessment rows found"
        for row in rows[:3]:
            assessment_id = row.get_attribute("data-assessment-id")
            version = row.get_attribute("data-version")
            save_resp = member_page.request.post(
                f"{BASE_URL}/learning/assessment/{assessment_id}/save/",
                headers={
                    "Content-Type": "application/json",
                    "X-CSRFToken": _csrf(member_page),
                    "Referer": BASE_URL,
                },
                data=json.dumps({
                    "version": int(version),
                    "current_level": "1",
                    "target_level": "3",
                    "included": True,
                }),
            )
            assert save_resp.ok, f"assessment save failed: {save_resp.status} {save_resp.text()[:200]}"

        member_page.goto(f"{BASE_URL}/learning/assessment/", wait_until="networkidle")
        expect(member_page.locator("#assessed-count")).to_have_text("3")
        expect(member_page.locator("#included-count")).to_have_text("3")
        _screenshot(member_page, "02_member_assessment")

        # 4. Generate the learning plan (no UI button yet, use backend endpoint).
        response = _post(
            member_page,
            f"{BASE_URL}/learning/cycles/{cycle_id}/plan/generate/",
        )
        assert response.ok, f"plan generation failed: {response.status} {response.text()[:200]}"
        plan_url = response.url
        plan_id = _extract_id_from_url(plan_url, "/learning/plans/")

        # 5. Edit the first plan item and submit the plan.
        member_page.goto(plan_url, wait_until="networkidle")
        first_edit_form = member_page.locator("form[action^='/learning/plan-items/']").first
        first_edit_form.locator("textarea[name='task']").fill("Smoke journey learning task")
        first_edit_form.locator("textarea[name='acceptance_method']").fill("Smoke journey acceptance")
        first_edit_form.locator("button[type='submit']").click()
        member_page.wait_for_load_state("networkidle")

        item_id = _extract_id_from_url(member_page.content(), "/learning/plan-items/")

        member_page.locator(f"form[action='/learning/plans/{plan_id}/submit/'] button").click()
        member_page.wait_for_load_state("networkidle")
        assert "待 Buddy 审批" in member_page.content()
        _screenshot(member_page, "03_member_submit_plan")
        member_context.close()

        # 6. Buddy approves the plan.
        buddy_context = browser.new_context(ignore_https_errors=True)
        buddy_page = buddy_context.new_page()
        _accept_dialogs(buddy_page)
        _login(buddy_page, BUDDY_USER, BUDDY_PASS)

        buddy_page.goto(f"{BASE_URL}/learning/buddy/approvals/", wait_until="networkidle")
        buddy_page.locator(f"form[action='/learning/plans/{plan_id}/approve/'] button").click()
        buddy_page.wait_for_load_state("networkidle")
        assert "暂无待审批计划" in buddy_page.content()
        _screenshot(buddy_page, "04_buddy_approve_plan")
        buddy_context.close()

        # 7. Member adds progress and submits evidence.
        member_context2 = browser.new_context(ignore_https_errors=True)
        member_page2 = member_context2.new_page()
        _accept_dialogs(member_page2)
        _login(member_page2, MEMBER_USER, MEMBER_PASS)

        # Use the assessment page to obtain a CSRF token for direct POSTs.
        member_page2.goto(f"{BASE_URL}/learning/assessment/", wait_until="networkidle")

        progress_resp = _post(
            member_page2,
            f"{BASE_URL}/learning/plan-items/{item_id}/progress/",
            {"content": "Completed smoke journey module", "hours_spent": "2.5"},
        )
        assert progress_resp.ok, f"progress add failed: {progress_resp.status} {progress_resp.text()[:200]}"

        evidence_resp = _post(
            member_page2,
            f"{BASE_URL}/learning/plan-items/{item_id}/evidence/",
            {"note": "Smoke journey evidence", "link": "https://example.com/smoke"},
        )
        assert evidence_resp.ok, f"evidence submit failed: {evidence_resp.status}"

        member_page2.goto(
            f"{BASE_URL}/learning/plan-items/{item_id}/execution/", wait_until="networkidle"
        )
        assert "待验收" in member_page2.content()
        _screenshot(member_page2, "05_member_submit_evidence")
        member_context2.close()

        # 8. Buddy reviews and accepts the evidence.
        buddy_context2 = browser.new_context(ignore_https_errors=True)
        buddy_page2 = buddy_context2.new_page()
        _accept_dialogs(buddy_page2)
        _login(buddy_page2, BUDDY_USER, BUDDY_PASS)

        buddy_page2.goto(f"{BASE_URL}/learning/buddy/approvals/", wait_until="networkidle")
        review_form = buddy_page2.locator("form[action^='/learning/evidence/']").first
        review_form.locator("select[name='decision']").select_option("completed")
        review_form.locator("button[type='submit']").click()
        buddy_page2.wait_for_load_state("networkidle")
        _screenshot(buddy_page2, "06_buddy_review_evidence")
        buddy_context2.close()

        # 9. Member verifies the item is completed.
        member_context3 = browser.new_context(ignore_https_errors=True)
        member_page3 = member_context3.new_page()
        _login(member_page3, MEMBER_USER, MEMBER_PASS)
        member_page3.goto(
            f"{BASE_URL}/learning/plan-items/{item_id}/execution/", wait_until="networkidle"
        )
        assert "已完成" in member_page3.content()
        _screenshot(member_page3, "07_member_completed")
        member_context3.close()

        # 10. Leader archives the cycle via Django admin.
        leader_context2 = browser.new_context(ignore_https_errors=True)
        leader_page2 = leader_context2.new_page()
        _login(leader_page2, LEADER_USER, LEADER_PASS)
        leader_page2.goto(
            f"{BASE_URL}/admin/learning/learningcycle/{cycle_id}/change/",
            wait_until="networkidle",
        )
        leader_page2.locator("select[name='status']").select_option("archived")
        leader_page2.locator("input[name='_save']").click()
        leader_page2.wait_for_load_state("networkidle")
        assert "已归档" in leader_page2.content()
        _screenshot(leader_page2, "08_leader_archive_cycle")
        leader_context2.close()

        browser.close()


def test_smoke_journey():
    run_journey()


if __name__ == "__main__":
    try:
        run_journey()
        print("OK: smoke journey")
        sys.exit(0)
    except Exception as exc:
        print(f"FAIL: smoke journey - {exc}")
        sys.exit(1)
