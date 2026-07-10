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
        domain=l2, code=code, name=name, sort_order=1, is_active=True
    )


def _active_plan_with_completed_item():
    leader = _user("leader", "leader")
    member = _user("member", "member")
    buddy = _user("buddy", "buddy")

    capability = _capability()

    cycle = LearningCycle.objects.create(
        cycle_type=LearningCycle.Type.CALENDAR_YEAR,
        year=2026,
        created_by=leader,
    )
    cycle.add_participant(member)

    assign_buddy(member, buddy)

    assessment = Assessment.objects.get(
        cycle=cycle, member=member, capability_item=capability
    )
    assessment.included = True
    assessment.current_level = 1
    assessment.target_level = 3
    assessment.planned_month = dt.date(2026, 5, 1)
    assessment.save()

    plan = generate_plan(member, cycle)
    submit_plan(plan, member)
    approve_plan(plan, buddy)

    item = plan.items.get()
    item.execution_status = PlanItem.ExecutionStatus.COMPLETED
    item.save(update_fields=["execution_status"])

    return leader, member, cycle, plan, item


@pytest.mark.django_db
def test_leader_journey_end_to_end():
    leader, member, cycle, plan, item = _active_plan_with_completed_item()

    leader_client = Client()
    leader_client.force_login(leader)

    # Leader can access cycle admin page
    response = leader_client.get(reverse("learning:cycle_admin"))
    assert response.status_code == 200

    # Leader dashboard metrics are consistent
    response = leader_client.get(reverse("dashboard:leader"))
    assert response.status_code == 200

    metrics = response.context["metrics"]
    completed_qs = response.context["completed_items"]

    assert metrics["completed_items"] == completed_qs.count()
    assert metrics["total_items"] == 1

    # History page excludes active cycle
    response = leader_client.get(reverse("dashboard:history"))
    assert response.status_code == 200
    assert cycle not in response.context["cycles"]

    # After archiving, history page includes the cycle
    cycle.status = LearningCycle.Status.ARCHIVED
    cycle.save(update_fields=["status"])

    response = leader_client.get(reverse("dashboard:history"))
    assert response.status_code == 200
    assert cycle in response.context["cycles"]

    # Member cannot access leader dashboard
    member_client = Client()
    member_client.force_login(member)

    response = member_client.get(reverse("dashboard:leader"))
    assert response.status_code == 403
