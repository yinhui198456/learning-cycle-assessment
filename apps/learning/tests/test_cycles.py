import datetime as dt
from http import HTTPStatus

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db import transaction
from django.urls import reverse

from apps.learning.models import (
    Assessment,
    CapabilityCategory,
    CapabilityDomain,
    CapabilityItem,
    CycleParticipant,
    LearningCycle,
    LearningMaterial,
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
def member_client(client, member):
    client.force_login(member)
    return client


@pytest.fixture
def leader_client(client, leader):
    client.force_login(leader)
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
def inactive_capability_item(db):
    category = CapabilityCategory.objects.create(name="Management", sort_order=2)
    domain_l1 = CapabilityDomain.objects.create(
        category=category,
        code="M01",
        name="Mgmt L1",
        level=1,
        sort_order=1,
    )
    domain_l2 = CapabilityDomain.objects.create(
        category=category,
        code="M01.01",
        name="Mgmt L2",
        level=2,
        sort_order=1,
        parent=domain_l1,
    )
    return CapabilityItem.objects.create(
        domain=domain_l2,
        code="M01.01.01",
        name="Inactive Item",
        sort_order=1,
        is_active=False,
    )


# ---- Model and service tests ----


@pytest.mark.django_db
def test_calendar_year_cycle_computes_dates_and_name(leader):
    cycle = LearningCycle.objects.create(
        cycle_type=LearningCycle.Type.CALENDAR_YEAR,
        year=2026,
        created_by=leader,
    )
    assert cycle.start_date == dt.date(2026, 1, 1)
    assert cycle.end_date == dt.date(2026, 12, 31)
    assert cycle.name == "2026 年度学习周期"


@pytest.mark.django_db
def test_rolling_cycle_computes_inclusive_12_month_range_and_name(leader):
    cycle = LearningCycle.objects.create(
        cycle_type=LearningCycle.Type.ROLLING_12_MONTH,
        start_date=dt.date(2026, 7, 15),
        created_by=leader,
    )
    assert cycle.start_date == dt.date(2026, 7, 15)
    assert cycle.end_date == dt.date(2027, 7, 14)
    assert cycle.name == "2026-07-15 至 2027-07-14 学习周期"


@pytest.mark.django_db
def test_cycle_end_must_not_precede_start(leader):
    cycle = LearningCycle.objects.create(
        cycle_type=LearningCycle.Type.ROLLING_12_MONTH,
        start_date=dt.date(2026, 7, 15),
        created_by=leader,
    )
    cycle.end_date = dt.date(2026, 7, 14)
    with pytest.raises(Exception):
        cycle.save()


@pytest.mark.django_db
def test_cycle_participant_is_unique_per_cycle_and_member(
    leader, member, capability_item
):
    cycle = LearningCycle.objects.create(
        cycle_type=LearningCycle.Type.CALENDAR_YEAR,
        year=2026,
        created_by=leader,
    )
    CycleParticipant.objects.create(cycle=cycle, member=member)
    with pytest.raises(Exception):
        CycleParticipant.objects.create(cycle=cycle, member=member)


@pytest.mark.django_db
def test_create_cycle_creates_one_assessment_per_active_item(
    leader, member, capability_item, inactive_capability_item
):
    cycle = LearningCycle.objects.create(
        cycle_type=LearningCycle.Type.CALENDAR_YEAR,
        year=2026,
        created_by=leader,
    )
    CycleParticipant.objects.create(cycle=cycle, member=member)
    cycle.create_missing_assessments()

    assessments = Assessment.objects.filter(cycle=cycle, member=member)
    assert assessments.count() == 1
    assert assessments.first().capability_item == capability_item


@pytest.mark.django_db
def test_create_cycle_rejects_overlapping_active_cycle(
    leader, member, other_member, capability_item
):
    first = LearningCycle.objects.create(
        cycle_type=LearningCycle.Type.CALENDAR_YEAR,
        year=2026,
        created_by=leader,
    )
    first.add_participant(member)

    with pytest.raises(ValueError):
        LearningCycle.create_rolling_cycle(
            start_date=dt.date(2026, 6, 1),
            members=[member],
            created_by=leader,
        )

    second = LearningCycle.objects.create(
        cycle_type=LearningCycle.Type.CALENDAR_YEAR,
        year=2027,
        created_by=leader,
    )
    second.add_participant(other_member)
    assert second.participants.count() == 1


@pytest.mark.django_db
def test_create_cycle_rolls_back_on_participant_failure(
    leader, member, capability_item
):
    inactive_member = _user("inactive-member", is_active=False)
    _add_role(inactive_member, "member")

    with pytest.raises(ValueError):
        LearningCycle.create_calendar_year(
            year=2026,
            members=[member, inactive_member],
            created_by=leader,
        )

    assert not LearningCycle.objects.filter(name="2026 年度学习周期").exists()
    assert not Assessment.objects.exists()


@pytest.mark.django_db
def test_only_active_members_can_be_added(leader, member, capability_item):
    inactive_member = _user("inactive-member-2", is_active=False)
    _add_role(inactive_member, "member")
    non_member = _user("non-member")

    cycle = LearningCycle.objects.create(
        cycle_type=LearningCycle.Type.CALENDAR_YEAR,
        year=2026,
        created_by=leader,
    )

    with pytest.raises(ValueError):
        cycle.add_participant(inactive_member)

    with pytest.raises(ValueError):
        cycle.add_participant(non_member)

    cycle.add_participant(member)
    assert cycle.participants.count() == 1


# ---- View tests ----


@pytest.mark.django_db
def test_anonymous_user_redirected_from_cycle_admin(client):
    response = client.get(reverse("learning:cycle_admin"))
    assert response.status_code == HTTPStatus.FOUND
    assert response.url.startswith(reverse("login"))


@pytest.mark.django_db
def test_member_is_forbidden_from_cycle_admin(member_client):
    response = member_client.get(reverse("learning:cycle_admin"))
    assert response.status_code == HTTPStatus.FORBIDDEN


@pytest.mark.django_db
def test_leader_can_access_cycle_admin(leader_client):
    response = leader_client.get(reverse("learning:cycle_admin"))
    assert response.status_code == HTTPStatus.OK


@pytest.mark.django_db
def test_leader_can_create_calendar_year_cycle(
    leader_client, leader, member, capability_item
):
    response = leader_client.post(
        reverse("learning:cycle_admin"),
        {
            "cycle_type": LearningCycle.Type.CALENDAR_YEAR,
            "year": 2026,
            "members": [member.pk],
        },
    )
    assert response.status_code == HTTPStatus.FOUND

    cycle = LearningCycle.objects.get()
    assert cycle.cycle_type == LearningCycle.Type.CALENDAR_YEAR
    assert cycle.name == "2026 年度学习周期"
    assert cycle.created_by == leader
    assert cycle.participants.filter(member=member).exists()
    assert Assessment.objects.filter(cycle=cycle, member=member).count() == 1


@pytest.mark.django_db
def test_leader_can_create_rolling_cycle(
    leader_client, leader, member, capability_item
):
    response = leader_client.post(
        reverse("learning:cycle_admin"),
        {
            "cycle_type": LearningCycle.Type.ROLLING_12_MONTH,
            "start_date": "2026-07-15",
            "members": [member.pk],
        },
    )
    assert response.status_code == HTTPStatus.FOUND

    cycle = LearningCycle.objects.get()
    assert cycle.cycle_type == LearningCycle.Type.ROLLING_12_MONTH
    assert cycle.start_date == dt.date(2026, 7, 15)
    assert cycle.end_date == dt.date(2027, 7, 14)


@pytest.mark.django_db
def test_cycle_admin_lists_cycles_with_participant_count(
    leader_client, leader, member, capability_item
):
    cycle = LearningCycle.objects.create(
        cycle_type=LearningCycle.Type.CALENDAR_YEAR,
        year=2026,
        created_by=leader,
    )
    cycle.add_participant(member)

    response = leader_client.get(reverse("learning:cycle_admin"))
    assert response.status_code == HTTPStatus.OK
    assert cycle.name in response.content.decode()
    assert "1" in response.content.decode()


@pytest.mark.django_db
def test_cycle_form_rejects_overlapping_active_cycle(
    leader_client, leader, member, capability_item
):
    first = LearningCycle.objects.create(
        cycle_type=LearningCycle.Type.CALENDAR_YEAR,
        year=2026,
        created_by=leader,
    )
    first.add_participant(member)

    response = leader_client.post(
        reverse("learning:cycle_admin"),
        {
            "cycle_type": LearningCycle.Type.ROLLING_12_MONTH,
            "start_date": "2026-06-01",
            "members": [member.pk],
        },
    )
    assert response.status_code == HTTPStatus.OK
    assert LearningCycle.objects.count() == 1


@pytest.mark.django_db
def test_cycle_form_ignores_neither_conflicting_field(
    leader_client, leader, member, capability_item
):
    response = leader_client.post(
        reverse("learning:cycle_admin"),
        {
            "cycle_type": LearningCycle.Type.CALENDAR_YEAR,
            "members": [member.pk],
        },
    )
    assert response.status_code == HTTPStatus.OK
    assert LearningCycle.objects.count() == 0

    response = leader_client.post(
        reverse("learning:cycle_admin"),
        {
            "cycle_type": LearningCycle.Type.ROLLING_12_MONTH,
            "members": [member.pk],
        },
    )
    assert response.status_code == HTTPStatus.OK
    assert LearningCycle.objects.count() == 0
