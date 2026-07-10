import datetime as dt
from http import HTTPStatus

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.urls import reverse

from apps.accounts.services import assign_buddy
from apps.learning.models import (
    Assessment,
    CapabilityCategory,
    CapabilityDomain,
    CapabilityItem,
    CapabilityMaterial,
    LearningCycle,
    LearningMaterial,
    LearningPlan,
    PlanItem,
)
from apps.learning.services_planning import generate_plan

User = get_user_model()


def _user(username):
    return User.objects.create_user(username=username, password="testpass123")


def _add_role(user, role_name):
    user.groups.add(Group.objects.get(name=role_name))


@pytest.fixture
def member(db):
    user = _user("member")
    _add_role(user, "member")
    return user


@pytest.fixture
def buddy(db):
    user = _user("buddy")
    _add_role(user, "buddy")
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
def cycle(db, leader, member, capability_items):
    cycle = LearningCycle.objects.create(
        cycle_type=LearningCycle.Type.CALENDAR_YEAR,
        year=2026,
        created_by=leader,
    )
    cycle.add_participant(member)
    return cycle


@pytest.fixture
def capability_items(db):
    category = CapabilityCategory.objects.create(name="Tech", sort_order=1)
    l1 = CapabilityDomain.objects.create(
        category=category, code="T01", name="Backend", level=1, sort_order=1
    )
    l2 = CapabilityDomain.objects.create(
        category=category,
        parent=l1,
        code="T01.01",
        name="API",
        level=2,
        sort_order=1,
    )
    item_one = CapabilityItem.objects.create(
        domain=l2,
        code="T01.01.01",
        name="Contract Design",
        suggested_level="P6",
        acceptance_method="Design review",
        estimated_hours="12",
        recommended_action="Read and practice",
        sort_order=1,
        is_active=True,
    )
    item_two = CapabilityItem.objects.create(
        domain=l2,
        code="T01.01.02",
        name="Capacity Planning",
        suggested_level="P7",
        acceptance_method="Capacity report",
        estimated_hours="8",
        sort_order=2,
        is_active=True,
    )
    material = LearningMaterial.objects.create(
        code="MAT-1",
        name="API Book",
        material_type="book",
        source="internal wiki",
    )
    CapabilityMaterial.objects.create(item=item_one, material=material, sort_order=1)
    return item_one, item_two


@pytest.fixture
def assessed_cycle(cycle, member, buddy, capability_items):
    assign_buddy(member, buddy)
    item_one, item_two = capability_items
    a1 = Assessment.objects.get(cycle=cycle, member=member, capability_item=item_one)
    a1.current_level = 1
    a1.target_level = 3
    a1.priority = "high"
    a1.included = True
    a1.planned_quarter = "Q2"
    a1.planned_month = dt.date(2026, 5, 1)
    a1.save()
    a2 = Assessment.objects.get(cycle=cycle, member=member, capability_item=item_two)
    a2.current_level = 2
    a2.target_level = 2
    a2.included = False
    a2.save()
    return cycle


@pytest.mark.django_db
def test_generate_plan_snapshots_only_included_assessments(assessed_cycle, member, buddy):
    plan = generate_plan(member, assessed_cycle)

    assert plan.status == LearningPlan.Status.DRAFT
    assert plan.buddy == buddy
    assert plan.items.count() == 1

    item = plan.items.get()
    assert item.capability_code == "T01.01.01"
    assert item.capability_name == "Contract Design"
    assert item.suggested_level == "P6"
    assert item.current_level == 1
    assert item.target_level == 3
    assert item.gap == 2
    assert item.priority == "high"
    assert item.planned_quarter == "Q2"
    assert item.planned_month == dt.date(2026, 5, 1)
    assert item.acceptance_method == "Design review"
    assert item.estimated_hours == "12"
    assert "MAT-1" in item.materials_snapshot
    assert "API Book" in item.materials_snapshot


@pytest.mark.django_db
def test_plan_snapshot_survives_capability_catalog_change(assessed_cycle, member):
    plan = generate_plan(member, assessed_cycle)
    source = plan.items.get().capability_item
    source.name = "Changed Name"
    source.acceptance_method = "Changed Method"
    source.save()

    item = PlanItem.objects.get(plan=plan)
    assert item.capability_name == "Contract Design"
    assert item.acceptance_method == "Design review"


@pytest.mark.django_db
def test_generate_plan_requires_current_buddy(cycle, member, capability_items):
    item_one, _ = capability_items
    assessment = Assessment.objects.get(cycle=cycle, member=member, capability_item=item_one)
    assessment.included = True
    assessment.save()

    with pytest.raises(ValueError, match="current Buddy"):
        generate_plan(member, cycle)


@pytest.mark.django_db
def test_generate_plan_replaces_draft_items_but_not_active_plan(assessed_cycle, member):
    plan = generate_plan(member, assessed_cycle)
    item = plan.items.get()
    item.task = "old task"
    item.save()

    same_plan = generate_plan(member, assessed_cycle)
    assert same_plan.pk == plan.pk
    assert same_plan.items.get().task == "Read and practice"

    same_plan.status = LearningPlan.Status.ACTIVE
    same_plan.save()
    with pytest.raises(ValueError, match="cannot be regenerated"):
        generate_plan(member, assessed_cycle)


@pytest.mark.django_db
def test_member_can_generate_plan_from_view(member_client, assessed_cycle):
    response = member_client.post(
        reverse("learning:plan-generate", args=[assessed_cycle.pk])
    )

    assert response.status_code == HTTPStatus.FOUND
    assert LearningPlan.objects.count() == 1


@pytest.mark.django_db
def test_generate_plan_view_returns_conflict_without_current_buddy(
    member_client, cycle, member, capability_items
):
    item_one, _ = capability_items
    assessment = Assessment.objects.get(cycle=cycle, member=member, capability_item=item_one)
    assessment.included = True
    assessment.save()

    response = member_client.post(reverse("learning:plan-generate", args=[cycle.pk]))

    assert response.status_code == HTTPStatus.CONFLICT
