import datetime as dt

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import Client
from django.urls import reverse

from apps.accounts.services import assign_buddy
from apps.learning.models import (
    Assessment,
    CapabilityCategory,
    CapabilityDomain,
    CapabilityItem,
    LearningCycle,
    PlanItem,
)
from apps.learning.services_planning import approve_plan, generate_plan, submit_plan

User = get_user_model()


def _user(username, role):
    user = User.objects.create_user(username=username, password="testpass123")
    user.groups.add(Group.objects.get(name=role))
    return user


def _capability(code="T01.01.01", name="Contracts"):
    category = CapabilityCategory.objects.create(name=f"Tech {code}", sort_order=1)
    l1 = CapabilityDomain.objects.create(
        category=category, code=code[:3], name="Backend", level=1, sort_order=1
    )
    l2 = CapabilityDomain.objects.create(
        category=category, parent=l1, code=code[:6], name="API", level=2, sort_order=1
    )
    return CapabilityItem.objects.create(
        domain=l2, code=code, name=name, sort_order=1
    )


def _active_plan(member, buddy, leader, item, year=2026, month=dt.date(2026, 5, 1)):
    assign_buddy(member, buddy)
    cycle = LearningCycle.objects.create(
        cycle_type=LearningCycle.Type.CALENDAR_YEAR,
        year=year,
        created_by=leader,
    )
    cycle.add_participant(member)
    assessment = Assessment.objects.get(cycle=cycle, member=member, capability_item=item)
    assessment.current_level = 1
    assessment.target_level = 3
    assessment.included = True
    assessment.planned_month = month
    assessment.save()
    plan = generate_plan(member, cycle)
    submit_plan(plan, member)
    approve_plan(plan, buddy)
    return plan


@pytest.fixture
def leader_client(db):
    leader = _user("leader", "leader")
    member = _user("member", "member")
    buddy = _user("buddy", "buddy")
    plan = _active_plan(member, buddy, leader, _capability())
    plan.items.update(execution_status=PlanItem.ExecutionStatus.COMPLETED)
    client = Client()
    client.force_login(leader)
    return client


@pytest.mark.django_db
def test_leader_completion_metric_matches_drilldown(leader_client):
    response = leader_client.get(reverse("dashboard:leader"))

    metric = response.context["metrics"]["completed_items"]
    drilldown = response.context["completed_items"]

    assert response.status_code == 200
    assert metric == drilldown.count()
