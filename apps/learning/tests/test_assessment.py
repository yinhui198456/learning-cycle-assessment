import datetime as dt
import json
from http import HTTPStatus

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.urls import reverse

from apps.learning.models import (
    Assessment,
    CapabilityCategory,
    CapabilityDomain,
    CapabilityItem,
    CapabilityMaterial,
    CycleParticipant,
    LearningCycle,
)

User = get_user_model()


def _user(username, is_active=True):
    return User.objects.create_user(
        username=username, password="testpass123", is_active=is_active
    )


def _add_role(user, role_name):
    group = Group.objects.get(name=role_name)
    user.groups.add(group)


@pytest.fixture
def member(db):
    user = _user("member")
    _add_role(user, "member")
    return user


@pytest.fixture
def other_member(db):
    user = _user("other-member")
    _add_role(user, "member")
    return user


@pytest.fixture
def leader(db):
    user = _user("leader")
    _add_role(user, "leader")
    return user


@pytest.fixture
def buddy(db):
    user = _user("buddy")
    _add_role(user, "buddy")
    return user


@pytest.fixture
def member_client(client, member):
    client.force_login(member)
    return client


@pytest.fixture
def other_member_client(client, other_member):
    client.force_login(other_member)
    return client


@pytest.fixture
def leader_client(client, leader):
    client.force_login(leader)
    return client


@pytest.fixture
def buddy_client(client, buddy):
    client.force_login(buddy)
    return client


@pytest.fixture
def capability_item(db):
    category = CapabilityCategory.objects.create(name="Tech", sort_order=1)
    domain_l1 = CapabilityDomain.objects.create(
        category=category,
        code="T01",
        name="Level One",
        level=1,
        sort_order=1,
    )
    domain_l2 = CapabilityDomain.objects.create(
        category=category,
        code="T01.01",
        name="Level Two",
        level=2,
        sort_order=1,
        parent=domain_l1,
    )
    return CapabilityItem.objects.create(
        domain=domain_l2,
        code="T01.01.01",
        name="Item One",
        sort_order=1,
        is_active=True,
    )


@pytest.fixture
def cycle_with_member(db, leader, member, capability_item):
    cycle = LearningCycle.objects.create(
        cycle_type=LearningCycle.Type.CALENDAR_YEAR,
        year=2026,
        created_by=leader,
    )
    cycle.add_participant(member)
    return cycle


@pytest.fixture
def member_assessment(db, cycle_with_member, member):
    return Assessment.objects.get(cycle=cycle_with_member, member=member)


@pytest.fixture
def other_member_assessment(db, cycle_with_member, other_member, capability_item):
    cycle_with_member.add_participant(other_member)
    return Assessment.objects.get(cycle=cycle_with_member, member=other_member)


# ---- Page permissions and routing ----


@pytest.mark.django_db
def test_anonymous_user_redirected_from_assessment(client):
    response = client.get(reverse("learning:assessment"))
    assert response.status_code == HTTPStatus.FOUND
    assert response.url.startswith(reverse("login"))


@pytest.mark.django_db
def test_non_member_gets_forbidden_on_assessment(leader_client):
    response = leader_client.get(reverse("learning:assessment"))
    assert response.status_code == HTTPStatus.FORBIDDEN


@pytest.mark.django_db
def test_member_sees_empty_state_when_no_cycle(member_client):
    response = member_client.get(reverse("learning:assessment"))
    assert response.status_code == HTTPStatus.OK
    content = response.content.decode()
    assert "当前没有参与的学习周期" in content


@pytest.mark.django_db
def test_member_page_defaults_to_active_cycle_containing_today(
    member_client, member, leader, capability_item
):
    today = dt.date.today()
    cycle = LearningCycle.objects.create(
        cycle_type=LearningCycle.Type.CALENDAR_YEAR,
        year=today.year,
        created_by=leader,
    )
    cycle.add_participant(member)

    response = member_client.get(reverse("learning:assessment"))
    assert response.status_code == HTTPStatus.OK
    assert cycle.name in response.content.decode()


@pytest.mark.django_db
def test_member_page_uses_query_param_cycle(
    member_client, member, leader, capability_item
):
    first = LearningCycle.objects.create(
        cycle_type=LearningCycle.Type.CALENDAR_YEAR,
        year=2025,
        created_by=leader,
    )
    first.add_participant(member)
    second = LearningCycle.objects.create(
        cycle_type=LearningCycle.Type.CALENDAR_YEAR,
        year=2026,
        created_by=leader,
    )
    second.add_participant(member)

    response = member_client.get(
        reverse("learning:assessment"), {"cycle": second.pk}
    )
    assert response.status_code == HTTPStatus.OK
    assert second.name in response.content.decode()
    assert first.name not in response.content.decode()


@pytest.mark.django_db
def test_assessment_page_backfills_missing_assessments(
    member_client, member, leader, capability_item
):
    cycle = LearningCycle.objects.create(
        cycle_type=LearningCycle.Type.CALENDAR_YEAR,
        year=2026,
        created_by=leader,
    )
    cycle.add_participant(member)

    category = CapabilityCategory.objects.create(name="New", sort_order=2)
    l1 = CapabilityDomain.objects.create(
        category=category, code="N01", name="New L1", level=1, sort_order=1
    )
    l2 = CapabilityDomain.objects.create(
        category=category,
        code="N01.01",
        name="New L2",
        level=2,
        sort_order=1,
        parent=l1,
    )
    new_item = CapabilityItem.objects.create(
        domain=l2, code="N01.01.01", name="New Item", sort_order=1, is_active=True
    )

    assert Assessment.objects.filter(cycle=cycle, member=member).count() == 1
    response = member_client.get(reverse("learning:assessment"), {"cycle": cycle.pk})
    assert response.status_code == HTTPStatus.OK
    assert Assessment.objects.filter(cycle=cycle, member=member).count() == 2
    assert Assessment.objects.filter(
        cycle=cycle, member=member, capability_item=new_item
    ).exists()


# ---- Single-row save permissions and validation ----


@pytest.mark.django_db
def test_member_cannot_update_another_members_assessment(
    member_client, member_assessment, other_member_assessment
):
    response = member_client.post(
        reverse("learning:assessment-save", args=[other_member_assessment.pk]),
        data=json.dumps({"current_level": 2, "target_level": 3, "version": 0}),
        content_type="application/json",
    )
    assert response.status_code == HTTPStatus.NOT_FOUND


@pytest.mark.django_db
def test_leader_cannot_use_member_save_endpoint(
    leader_client, member_assessment
):
    response = leader_client.post(
        reverse("learning:assessment-save", args=[member_assessment.pk]),
        data=json.dumps({"current_level": 2, "target_level": 3, "version": 0}),
        content_type="application/json",
    )
    assert response.status_code == HTTPStatus.FORBIDDEN


@pytest.mark.django_db
def test_buddy_cannot_use_member_save_endpoint(
    buddy_client, member_assessment
):
    response = buddy_client.post(
        reverse("learning:assessment-save", args=[member_assessment.pk]),
        data=json.dumps({"current_level": 2, "target_level": 3, "version": 0}),
        content_type="application/json",
    )
    assert response.status_code == HTTPStatus.FORBIDDEN


@pytest.mark.django_db
def test_archived_cycle_returns_conflict_on_single_save(
    member_client, member_assessment, cycle_with_member
):
    cycle_with_member.status = LearningCycle.Status.ARCHIVED
    cycle_with_member.save()

    response = member_client.post(
        reverse("learning:assessment-save", args=[member_assessment.pk]),
        data=json.dumps({"current_level": 2, "target_level": 3, "version": 0}),
        content_type="application/json",
    )
    assert response.status_code == HTTPStatus.CONFLICT
    assert response.json()["error"] == "archived"


@pytest.mark.django_db
def test_invalid_level_returns_field_error(member_client, member_assessment):
    response = member_client.post(
        reverse("learning:assessment-save", args=[member_assessment.pk]),
        data=json.dumps({"current_level": 6, "target_level": 3, "version": 0}),
        content_type="application/json",
    )
    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert "current_level" in response.json()["errors"]


@pytest.mark.django_db
def test_invalid_target_level_returns_field_error(member_client, member_assessment):
    response = member_client.post(
        reverse("learning:assessment-save", args=[member_assessment.pk]),
        data=json.dumps({"current_level": 2, "target_level": 7, "version": 0}),
        content_type="application/json",
    )
    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert "target_level" in response.json()["errors"]


@pytest.mark.django_db
def test_invalid_priority_returns_field_error(member_client, member_assessment):
    response = member_client.post(
        reverse("learning:assessment-save", args=[member_assessment.pk]),
        data=json.dumps({"priority": "urgent", "version": 0}),
        content_type="application/json",
    )
    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert "priority" in response.json()["errors"]


# ---- Gap calculation and values ----


@pytest.mark.django_db
def test_gap_computed_as_target_minus_current(member_client, member_assessment):
    response = member_client.post(
        reverse("learning:assessment-save", args=[member_assessment.pk]),
        data=json.dumps({"current_level": 2, "target_level": 4, "version": 0}),
        content_type="application/json",
    )
    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert data["values"]["gap"] == 2
    assert data["values"]["current_level"] == 2
    assert data["values"]["target_level"] == 4


@pytest.mark.django_db
def test_gap_clamps_to_zero_when_target_below_current(
    member_client, member_assessment
):
    response = member_client.post(
        reverse("learning:assessment-save", args=[member_assessment.pk]),
        data=json.dumps({"current_level": 3, "target_level": 2, "version": 0}),
        content_type="application/json",
    )
    assert response.status_code == HTTPStatus.OK
    assert response.json()["values"]["gap"] == 0


@pytest.mark.django_db
def test_planned_month_normalized_to_first_day(member_client, member_assessment):
    response = member_client.post(
        reverse("learning:assessment-save", args=[member_assessment.pk]),
        data=json.dumps({"planned_month": "2026-07-15", "version": 0}),
        content_type="application/json",
    )
    assert response.status_code == HTTPStatus.OK
    assert response.json()["values"]["planned_month"] == "2026-07-01"


@pytest.mark.django_db
def test_save_increments_version_and_returns_counts(
    member_client, member_assessment, cycle_with_member, member
):
    response = member_client.post(
        reverse("learning:assessment-save", args=[member_assessment.pk]),
        data=json.dumps({"current_level": 2, "target_level": 4, "version": 0}),
        content_type="application/json",
    )
    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert data["version"] == 1
    assert data["counts"]["total"] == 1
    assert data["counts"]["assessed"] == 1
    assert data["counts"]["included"] == 0

    member_assessment.refresh_from_db()
    assert member_assessment.version == 1


# ---- Optimistic locking ----


@pytest.mark.django_db
def test_stale_version_returns_conflict_without_overwrite(
    member_client, member_assessment
):
    member_assessment.current_level = 1
    member_assessment.target_level = 2
    member_assessment.version = 1
    member_assessment.save()

    response = member_client.post(
        reverse("learning:assessment-save", args=[member_assessment.pk]),
        data=json.dumps({"current_level": 3, "target_level": 5, "version": 0}),
        content_type="application/json",
    )
    assert response.status_code == HTTPStatus.CONFLICT
    body = response.json()
    assert body["error"] == "conflict"
    assert body["version"] == 1
    assert body["values"]["current_level"] == 1
    assert body["values"]["target_level"] == 2

    member_assessment.refresh_from_db()
    assert member_assessment.current_level == 1
    assert member_assessment.target_level == 2


# ---- Batch save ----


@pytest.mark.django_db
def test_batch_update_applies_only_selected_assessments(
    member_client, cycle_with_member, member, capability_item
):
    category = CapabilityCategory.objects.create(name="Batch", sort_order=3)
    l1 = CapabilityDomain.objects.create(
        category=category, code="B01", name="Batch L1", level=1, sort_order=1
    )
    l2 = CapabilityDomain.objects.create(
        category=category,
        code="B01.01",
        name="Batch L2",
        level=2,
        sort_order=1,
        parent=l1,
    )
    item2 = CapabilityItem.objects.create(
        domain=l2, code="B01.01.01", name="Batch Item 2", sort_order=1, is_active=True
    )
    item3 = CapabilityItem.objects.create(
        domain=l2, code="B01.01.02", name="Batch Item 3", sort_order=2, is_active=True
    )
    cycle_with_member.create_missing_assessments()

    a1 = Assessment.objects.get(member=member, capability_item=capability_item)
    a2 = Assessment.objects.get(member=member, capability_item=item2)
    a3 = Assessment.objects.get(member=member, capability_item=item3)

    response = member_client.post(
        reverse("learning:assessment-batch"),
        data=json.dumps(
            {
                "ids": [a1.pk, a2.pk],
                "included": True,
                "priority": "high",
                "planned_quarter": "Q1",
                "planned_month": "2026-03-01",
            }
        ),
        content_type="application/json",
    )
    assert response.status_code == HTTPStatus.OK
    body = response.json()
    assert body["ok"] is True
    assert body["updated"] == 2
    assert body["counts"]["included"] == 2

    a1.refresh_from_db()
    a2.refresh_from_db()
    a3.refresh_from_db()
    assert a1.included is True
    assert a1.priority == "high"
    assert a1.planned_quarter == "Q1"
    assert a1.planned_month == dt.date(2026, 3, 1)
    assert a3.included is False
    assert a3.priority == ""


@pytest.mark.django_db
def test_batch_update_is_all_or_nothing_on_unauthorized_id(
    member_client, cycle_with_member, member, other_member, capability_item
):
    cycle_with_member.add_participant(other_member)
    cycle_with_member.create_missing_assessments()
    a_member = Assessment.objects.get(member=member, capability_item=capability_item)
    a_other = Assessment.objects.get(member=other_member, capability_item=capability_item)

    response = member_client.post(
        reverse("learning:assessment-batch"),
        data=json.dumps(
            {
                "ids": [a_member.pk, a_other.pk],
                "included": True,
            }
        ),
        content_type="application/json",
    )
    assert response.status_code == HTTPStatus.NOT_FOUND

    a_member.refresh_from_db()
    assert a_member.included is False


@pytest.mark.django_db
def test_batch_update_is_all_or_nothing_on_archived_cycle(
    member_client, member, leader, capability_item
):
    cycle = LearningCycle.objects.create(
        cycle_type=LearningCycle.Type.CALENDAR_YEAR,
        year=2026,
        created_by=leader,
    )
    cycle.add_participant(member)

    category = CapabilityCategory.objects.create(name="Arch", sort_order=4)
    l1 = CapabilityDomain.objects.create(
        category=category, code="A01", name="Arch L1", level=1, sort_order=1
    )
    l2 = CapabilityDomain.objects.create(
        category=category,
        code="A01.01",
        name="Arch L2",
        level=2,
        sort_order=1,
        parent=l1,
    )
    item2 = CapabilityItem.objects.create(
        domain=l2, code="A01.01.01", name="Arch Item 2", sort_order=1, is_active=True
    )
    cycle.create_missing_assessments()
    cycle.status = LearningCycle.Status.ARCHIVED
    cycle.save()

    a1, a2 = list(Assessment.objects.filter(member=member, cycle=cycle))

    response = member_client.post(
        reverse("learning:assessment-batch"),
        data=json.dumps(
            {
                "ids": [a1.pk, a2.pk],
                "included": True,
            }
        ),
        content_type="application/json",
    )
    assert response.status_code == HTTPStatus.CONFLICT

    for assessment in Assessment.objects.filter(member=member, cycle=cycle):
        assert assessment.included is False


@pytest.mark.django_db
def test_batch_rejects_mixed_cycles(
    member_client, member, leader, capability_item
):
    first = LearningCycle.objects.create(
        cycle_type=LearningCycle.Type.CALENDAR_YEAR,
        year=2026,
        created_by=leader,
    )
    first.add_participant(member)
    second = LearningCycle.objects.create(
        cycle_type=LearningCycle.Type.CALENDAR_YEAR,
        year=2027,
        created_by=leader,
    )
    second.add_participant(member)

    category = CapabilityCategory.objects.create(name="Mix", sort_order=5)
    l1 = CapabilityDomain.objects.create(
        category=category, code="M01", name="Mix L1", level=1, sort_order=1
    )
    l2 = CapabilityDomain.objects.create(
        category=category,
        code="M01.01",
        name="Mix L2",
        level=2,
        sort_order=1,
        parent=l1,
    )
    item2 = CapabilityItem.objects.create(
        domain=l2, code="M01.01.01", name="Mix Item 2", sort_order=1, is_active=True
    )
    first.create_missing_assessments()
    second.create_missing_assessments()

    a_first = Assessment.objects.get(member=member, cycle=first, capability_item=capability_item)
    a_second = Assessment.objects.get(
        member=member, cycle=second, capability_item=item2
    )

    response = member_client.post(
        reverse("learning:assessment-batch"),
        data=json.dumps(
            {
                "ids": [a_first.pk, a_second.pk],
                "included": True,
            }
        ),
        content_type="application/json",
    )
    assert response.status_code == HTTPStatus.BAD_REQUEST


# ---- Template contract ----


@pytest.mark.django_db
def test_dense_controls_render_on_assessment_page(
    member_client, cycle_with_member
):
    response = member_client.get(reverse("learning:assessment"))
    assert response.status_code == HTTPStatus.OK
    content = response.content.decode()
    assert "assessment-table" in content
    assert 'id="select-all"' in content
    assert 'id="batch-apply"' in content
    assert 'id="filter-gap"' in content
    assert 'id="filter-priority"' in content
    assert 'id="filter-included"' in content
    assert 'id="filter-filled"' in content
    assert "row-status" in content
    assert "retry-button" in content


@pytest.mark.django_db
def test_assessment_page_includes_static_assets(
    member_client, cycle_with_member
):
    response = member_client.get(reverse("learning:assessment"))
    assert response.status_code == HTTPStatus.OK
    content = response.content.decode()
    assert "learning/assessment.css" in content
    assert "learning/assessment.js" in content


# ---- Query count ----


@pytest.mark.django_db
def test_assessment_page_query_count_is_bounded(
    django_assert_num_queries, member_client, member, leader
):
    category = CapabilityCategory.objects.create(name="Perf", sort_order=6)
    l1 = CapabilityDomain.objects.create(
        category=category, code="P01", name="Perf L1", level=1, sort_order=1
    )
    l2 = CapabilityDomain.objects.create(
        category=category,
        code="P01.01",
        name="Perf L2",
        level=2,
        sort_order=1,
        parent=l1,
    )
    CapabilityItem.objects.bulk_create(
        [
            CapabilityItem(
                domain=l2,
                code=f"P01.01.{i:03d}",
                name=f"Perf Item {i}",
                sort_order=i,
                is_active=True,
            )
            for i in range(1, 311)
        ]
    )

    cycle = LearningCycle.objects.create(
        cycle_type=LearningCycle.Type.CALENDAR_YEAR,
        year=2026,
        created_by=leader,
    )
    cycle.add_participant(member)

    with django_assert_num_queries(14):
        member_client.get(reverse("learning:assessment"))

    assert Assessment.objects.filter(cycle=cycle, member=member).count() == 310


# ---- Specification review fixes ----


def _static_text(filename):
    from pathlib import Path
    return (Path(__file__).resolve().parents[3] / "apps" / "learning" / "static" / "learning" / filename).read_text()


@pytest.mark.django_db
def test_capability_material_admin_registered():
    from django.contrib import admin
    assert admin.site.is_registered(CapabilityMaterial)


@pytest.mark.django_db
def test_assessment_page_has_all_filter_controls(member_client, cycle_with_member):
    response = member_client.get(reverse("learning:assessment"))
    content = response.content.decode()
    required = [
        "filter-category",
        "filter-domain-l1",
        "filter-domain-l2",
        "filter-suggested-level",
        "filter-gap",
        "filter-priority",
        "filter-included",
        "filter-filled",
    ]
    for fid in required:
        assert f'id="{fid}"' in content, fid


@pytest.mark.django_db
def test_assessment_rows_expose_filter_data_attributes(member_client, cycle_with_member):
    response = member_client.get(reverse("learning:assessment"))
    content = response.content.decode()
    assert "data-domain-l1=" in content
    assert "data-domain-l2=" in content
    assert "data-suggested-level=" in content
    assert "data-gap=" in content
    assert "data-priority=" in content
    assert "data-included=" in content
    assert "data-filled=" in content


def test_assessment_js_has_filter_hooks_and_populate_options():
    source = _static_text("assessment.js")
    assert "filter-domain-l1" in source
    assert "filter-domain-l2" in source
    assert "filter-suggested-level" in source
    assert "applyFilters" in source
    assert "populateFilterOptions" in source


def test_assessment_js_autosave_bound_to_editable_controls_only():
    source = _static_text("assessment.js")
    assert ".field-current-level" in source
    assert ".field-target-level" in source
    assert ".field-priority" in source
    assert ".field-included" in source
    assert ".field-quarter" in source
    assert ".field-month" in source
    # The generic "select, input" listener that would catch the row checkbox is gone.
    assert "querySelectorAll('select, input')" not in source


def test_assessment_js_retry_uses_current_controls():
    source = _static_text("assessment.js")
    assert "_retryData" not in source
    assert 'data-field="' not in source


def test_assessment_css_has_focus_visible_and_status_selectors():
    css = _static_text("assessment.css")
    assert ":focus-visible" in css
    assert '.row-status[data-status="idle"]' in css or ".row-status[data-status=\"idle\"]" in css
    assert ".row-status [data-status=" not in css


@pytest.mark.django_db
def test_single_save_updates_updated_at(member_client, member_assessment):
    from datetime import timedelta
    from django.utils import timezone

    Assessment.objects.filter(pk=member_assessment.pk).update(
        updated_at=timezone.now() - timedelta(hours=1)
    )
    response = member_client.post(
        reverse("learning:assessment-save", args=[member_assessment.pk]),
        data=json.dumps({"current_level": 2, "target_level": 4, "version": 0}),
        content_type="application/json",
    )
    assert response.status_code == HTTPStatus.OK
    member_assessment.refresh_from_db()
    assert member_assessment.updated_at >= timezone.now() - timedelta(minutes=1)


@pytest.mark.django_db
def test_batch_save_increments_version_and_updated_at(
    member_client, cycle_with_member, member, capability_item
):
    from datetime import timedelta
    from django.utils import timezone

    category = CapabilityCategory.objects.create(name="BatchVer", sort_order=7)
    l1 = CapabilityDomain.objects.create(
        category=category, code="BV01", name="BatchVer L1", level=1, sort_order=1
    )
    l2 = CapabilityDomain.objects.create(
        category=category,
        code="BV01.01",
        name="BatchVer L2",
        level=2,
        sort_order=1,
        parent=l1,
    )
    item2 = CapabilityItem.objects.create(
        domain=l2, code="BV01.01.01", name="BatchVer Item 2", sort_order=1, is_active=True
    )
    cycle_with_member.create_missing_assessments()

    a1 = Assessment.objects.get(member=member, capability_item=capability_item)
    a2 = Assessment.objects.get(member=member, capability_item=item2)
    Assessment.objects.filter(pk__in=[a1.pk, a2.pk]).update(
        updated_at=timezone.now() - timedelta(hours=1)
    )

    response = member_client.post(
        reverse("learning:assessment-batch"),
        data=json.dumps({"ids": [a1.pk, a2.pk], "included": True}),
        content_type="application/json",
    )
    assert response.status_code == HTTPStatus.OK
    a1.refresh_from_db()
    a2.refresh_from_db()
    assert a1.version == 1
    assert a2.version == 1
    assert a1.updated_at >= timezone.now() - timedelta(minutes=1)
    assert a2.updated_at >= timezone.now() - timedelta(minutes=1)


@pytest.mark.django_db
def test_single_save_missing_version_returns_400(member_client, member_assessment):
    response = member_client.post(
        reverse("learning:assessment-save", args=[member_assessment.pk]),
        data=json.dumps({"current_level": 2, "target_level": 4}),
        content_type="application/json",
    )
    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert "version" in response.json()["errors"]


@pytest.mark.django_db
def test_single_save_non_integer_version_returns_400(member_client, member_assessment):
    response = member_client.post(
        reverse("learning:assessment-save", args=[member_assessment.pk]),
        data=json.dumps({"current_level": 2, "target_level": 4, "version": "abc"}),
        content_type="application/json",
    )
    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert "version" in response.json()["errors"]


@pytest.mark.django_db
def test_single_save_malformed_json_returns_400(member_client, member_assessment):
    response = member_client.post(
        reverse("learning:assessment-save", args=[member_assessment.pk]),
        data="not json",
        content_type="application/json",
    )
    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert "errors" in response.json()


@pytest.mark.django_db
def test_single_save_invalid_utf8_json_returns_400(member_client, member_assessment):
    response = member_client.post(
        reverse("learning:assessment-save", args=[member_assessment.pk]),
        data=b"\xff",
        content_type="application/json",
    )
    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert "errors" in response.json()


@pytest.mark.django_db
def test_single_save_non_object_json_returns_400(member_client, member_assessment):
    response = member_client.post(
        reverse("learning:assessment-save", args=[member_assessment.pk]),
        data="42",
        content_type="application/json",
    )
    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert "errors" in response.json()


@pytest.mark.django_db
def test_single_save_non_numeric_level_returns_field_error(member_client, member_assessment):
    response = member_client.post(
        reverse("learning:assessment-save", args=[member_assessment.pk]),
        data=json.dumps({"current_level": "abc", "version": 0}),
        content_type="application/json",
    )
    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert "current_level" in response.json()["errors"]


@pytest.mark.django_db
def test_batch_save_non_numeric_id_returns_400(member_client, cycle_with_member):
    response = member_client.post(
        reverse("learning:assessment-batch"),
        data=json.dumps({"ids": ["abc"], "included": True}),
        content_type="application/json",
    )
    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert "ids" in response.json()["errors"]


@pytest.mark.django_db
def test_single_save_invalid_date_returns_field_error(member_client, member_assessment):
    response = member_client.post(
        reverse("learning:assessment-save", args=[member_assessment.pk]),
        data=json.dumps({"planned_month": "not-a-date", "version": 0}),
        content_type="application/json",
    )
    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert "planned_month" in response.json()["errors"]


@pytest.mark.django_db
def test_single_save_invalid_boolean_returns_field_error(member_client, member_assessment):
    response = member_client.post(
        reverse("learning:assessment-save", args=[member_assessment.pk]),
        data=json.dumps({"included": "maybe", "version": 0}),
        content_type="application/json",
    )
    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert "included" in response.json()["errors"]


@pytest.mark.django_db
def test_single_save_accepts_month_input_yyyy_mm(member_client, member_assessment):
    response = member_client.post(
        reverse("learning:assessment-save", args=[member_assessment.pk]),
        data=json.dumps({"planned_month": "2026-07", "version": 0}),
        content_type="application/json",
    )
    assert response.status_code == HTTPStatus.OK
    assert response.json()["values"]["planned_month"] == "2026-07-01"


@pytest.mark.django_db
def test_single_save_orphan_assessment_returns_404(member_client, member, leader, capability_item):
    cycle = LearningCycle.objects.create(
        cycle_type=LearningCycle.Type.CALENDAR_YEAR,
        year=2026,
        created_by=leader,
    )
    assessment = Assessment.objects.create(
        cycle=cycle, member=member, capability_item=capability_item
    )
    response = member_client.post(
        reverse("learning:assessment-save", args=[assessment.pk]),
        data=json.dumps({"current_level": 2, "target_level": 4, "version": 0}),
        content_type="application/json",
    )
    assert response.status_code == HTTPStatus.NOT_FOUND
    assessment.refresh_from_db()
    assert assessment.current_level is None
    assert assessment.target_level is None
    assert assessment.version == 0


@pytest.mark.django_db
def test_batch_save_orphan_assessment_returns_404(
    member_client, member, leader, capability_item
):
    cycle = LearningCycle.objects.create(
        cycle_type=LearningCycle.Type.CALENDAR_YEAR,
        year=2026,
        created_by=leader,
    )
    assessment = Assessment.objects.create(
        cycle=cycle, member=member, capability_item=capability_item
    )
    response = member_client.post(
        reverse("learning:assessment-batch"),
        data=json.dumps({"ids": [assessment.pk], "included": True}),
        content_type="application/json",
    )
    assert response.status_code == HTTPStatus.NOT_FOUND
    assessment.refresh_from_db()
    assert assessment.included is False


def test_assessment_js_formats_error_objects_readably():
    source = _static_text("assessment.js")
    assert "payload.errors ||" not in source
    assert "formatError" in source


def test_get_visible_cycles_for_is_removed():
    from apps.learning import services
    assert not hasattr(services, "get_visible_cycles_for")
