from datetime import date

from django.db import transaction
from django.utils import timezone

from apps.accounts.models import EmailLog, Mentorship

from .models import Assessment, LearningCycle, LearningPlan, PlanApprovalEvent, PlanItem


def _current_buddy(member):
    mentorship = (
        Mentorship.objects.filter(member=member, ended_at__isnull=True)
        .select_related("buddy")
        .first()
    )
    if mentorship is None:
        raise ValueError("Member must have a current Buddy.")
    return mentorship.buddy


def _materials_snapshot(capability_item):
    rows = []
    links = capability_item.capability_materials.select_related("material").order_by(
        "sort_order", "material__code"
    )
    for link in links:
        material = link.material
        rows.append(f"{material.code} - {material.name}")
    return "\n".join(rows)


def generate_plan(member, cycle):
    if cycle.status != LearningCycle.Status.ACTIVE:
        raise ValueError("Archived cycle cannot generate a plan.")
    if not cycle.participants.filter(member=member).exists():
        raise PermissionError("Member is not a cycle participant.")

    buddy = _current_buddy(member)
    assessments = list(
        Assessment.objects.filter(cycle=cycle, member=member, included=True)
        .select_related("capability_item")
        .order_by("capability_item__sort_order", "capability_item__code")
    )
    if not assessments:
        raise ValueError("Plan requires at least one included assessment.")

    with transaction.atomic():
        plan, _ = LearningPlan.objects.get_or_create(
            member=member,
            cycle=cycle,
            defaults={"buddy": buddy},
        )
        if plan.status in (
            LearningPlan.Status.PENDING_APPROVAL,
            LearningPlan.Status.ACTIVE,
        ):
            raise ValueError("Plan cannot be regenerated in its current status.")

        plan.buddy = buddy
        plan.status = LearningPlan.Status.DRAFT
        plan.approved_at = None
        plan.save(update_fields=["buddy", "status", "approved_at", "updated_at"])
        plan.items.all().delete()

        PlanItem.objects.bulk_create(
            [
                PlanItem(
                    plan=plan,
                    assessment=assessment,
                    capability_item=assessment.capability_item,
                    capability_code=assessment.capability_item.code,
                    capability_name=assessment.capability_item.name,
                    suggested_level=assessment.capability_item.suggested_level,
                    materials_snapshot=_materials_snapshot(assessment.capability_item),
                    current_level=assessment.current_level,
                    target_level=assessment.target_level,
                    gap=assessment.gap,
                    priority=assessment.priority,
                    planned_quarter=assessment.planned_quarter,
                    planned_month=assessment.planned_month,
                    task=assessment.capability_item.recommended_action,
                    acceptance_method=assessment.capability_item.acceptance_method,
                    estimated_hours=assessment.capability_item.estimated_hours,
                    sort_order=assessment.capability_item.sort_order,
                )
                for assessment in assessments
            ]
        )
    return plan


def submit_plan(plan, actor):
    if plan.member_id != actor.pk:
        raise PermissionError("Only the member can submit this plan.")
    if plan.status not in (
        LearningPlan.Status.DRAFT,
        LearningPlan.Status.CHANGES_REQUESTED,
    ):
        raise ValueError("Plan cannot be submitted in its current status.")
    if not plan.items.exists():
        raise ValueError("Plan cannot be submitted without items.")

    plan.status = LearningPlan.Status.PENDING_APPROVAL
    plan.submitted_at = timezone.now()
    plan.save(update_fields=["status", "submitted_at", "updated_at"])
    PlanApprovalEvent.objects.create(
        plan=plan,
        actor=actor,
        action=PlanApprovalEvent.Action.SUBMITTED,
    )
    EmailLog.objects.create_pending(
        recipient=plan.buddy,
        trigger="plan_submitted",
        subject="学习计划待审批",
        body=f"{plan.member.username} 已提交 {plan.cycle.name}，请审批。",
    )
    return plan


def _require_current_buddy(plan, actor):
    if plan.buddy_id != actor.pk:
        raise PermissionError("Only the current Buddy can decide this plan.")
    if not Mentorship.objects.filter(
        member=plan.member,
        buddy=actor,
        ended_at__isnull=True,
    ).exists():
        raise PermissionError("Only the current Buddy can decide this plan.")


def request_changes(plan, actor, comment):
    _require_current_buddy(plan, actor)
    if plan.status != LearningPlan.Status.PENDING_APPROVAL:
        raise ValueError("Buddy cannot request changes in the current status.")
    if not comment.strip():
        raise ValueError("A comment is required to request changes.")

    plan.status = LearningPlan.Status.CHANGES_REQUESTED
    plan.save(update_fields=["status", "updated_at"])
    PlanApprovalEvent.objects.create(
        plan=plan,
        actor=actor,
        action=PlanApprovalEvent.Action.CHANGES_REQUESTED,
        comment=comment.strip(),
    )
    EmailLog.objects.create_pending(
        recipient=plan.member,
        trigger="plan_changes_requested",
        subject="学习计划已退回",
        body=comment.strip(),
    )
    return plan


def approve_plan(plan, actor):
    _require_current_buddy(plan, actor)
    if plan.status != LearningPlan.Status.PENDING_APPROVAL:
        raise ValueError("Plan cannot be approved in its current status.")

    plan.status = LearningPlan.Status.ACTIVE
    plan.approved_at = timezone.now()
    plan.save(update_fields=["status", "approved_at", "updated_at"])
    PlanApprovalEvent.objects.create(
        plan=plan,
        actor=actor,
        action=PlanApprovalEvent.Action.APPROVED,
    )
    EmailLog.objects.create_pending(
        recipient=plan.member,
        trigger="plan_approved",
        subject="学习计划已审批通过",
        body=f"{plan.cycle.name} 已进入执行。",
    )
    return plan


def _normalize_month(value):
    if value in ("", None):
        return None
    if isinstance(value, str):
        if len(value) == 7 and value.count("-") == 1:
            value = f"{value}-01"
        value = date.fromisoformat(value)
    return value.replace(day=1)


def edit_plan_item(item, actor, data):
    if item.plan.member_id != actor.pk:
        raise PermissionError("Only the member can edit this plan item.")
    if item.plan.status not in (
        LearningPlan.Status.DRAFT,
        LearningPlan.Status.CHANGES_REQUESTED,
    ):
        raise ValueError("Active or pending plan items cannot be edited.")

    for field in ("task", "acceptance_method", "estimated_hours", "planned_quarter"):
        if field in data:
            setattr(item, field, data[field])
    if "planned_month" in data:
        item.planned_month = _normalize_month(data["planned_month"])
    item.save()
    return item
