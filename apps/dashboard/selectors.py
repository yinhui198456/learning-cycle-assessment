from datetime import timedelta

from django.db.models import Count, Q
from django.utils import timezone

from apps.learning.models import (
    EvidenceSubmission,
    LearningCycle,
    LearningPlan,
    PlanItem,
    ProgressUpdate,
    ReviewDecision,
)

STALE_DAYS = 30
REPEATED_CHANGES = 2


def active_cycles():
    return LearningCycle.objects.filter(status=LearningCycle.Status.ACTIVE)


def archived_cycles():
    return LearningCycle.objects.filter(status=LearningCycle.Status.ARCHIVED)


def active_plan_items():
    return PlanItem.objects.filter(plan__cycle__status=LearningCycle.Status.ACTIVE)


def completed_items():
    return active_plan_items().filter(execution_status=PlanItem.ExecutionStatus.COMPLETED)


def overdue_items():
    month = timezone.localdate().replace(day=1)
    return active_plan_items().filter(planned_month__lt=month).exclude(
        execution_status=PlanItem.ExecutionStatus.COMPLETED
    )


def pending_plans(user=None):
    qs = LearningPlan.objects.filter(
        cycle__status=LearningCycle.Status.ACTIVE,
        status=LearningPlan.Status.PENDING_APPROVAL,
    )
    return qs.filter(buddy=user) if user else qs


def pending_reviews(user=None):
    qs = active_plan_items().filter(
        execution_status=PlanItem.ExecutionStatus.PENDING_REVIEW
    )
    return qs.filter(plan__buddy=user) if user else qs


def stale_items():
    cutoff = timezone.now() - timedelta(days=STALE_DAYS)
    progressed = ProgressUpdate.objects.values("plan_item_id")
    return active_plan_items().filter(updated_at__lt=cutoff).exclude(
        pk__in=progressed,
    ).exclude(execution_status=PlanItem.ExecutionStatus.COMPLETED)


def repeated_changes_items():
    return active_plan_items().annotate(
        change_count=Count(
            "evidence_submissions__review_decisions",
            filter=Q(
                evidence_submissions__review_decisions__decision=(
                    ReviewDecision.Decision.CHANGES_REQUESTED
                )
            ),
        )
    ).filter(change_count__gte=REPEATED_CHANGES)


def leader_metrics():
    total = active_plan_items().count()
    done = completed_items().count()
    return {
        "participants": active_cycles().values("participants__member").distinct().count(),
        "completed_items": done,
        "total_items": total,
        "completion_rate": round(done * 100 / total) if total else 0,
        "overdue_items": overdue_items().count(),
        "pending_plans": pending_plans().count(),
        "pending_reviews": pending_reviews().count(),
    }


def member_context(user):
    plans = LearningPlan.objects.filter(member=user).order_by("-cycle__start_date")
    plan = plans.filter(cycle__status=LearningCycle.Status.ACTIVE).first()
    items = plan.items.all() if plan else PlanItem.objects.none()
    return {
        "plan": plan,
        "items": items,
        "next_items": items.exclude(
            execution_status=PlanItem.ExecutionStatus.COMPLETED
        ).order_by("planned_month", "sort_order")[:5],
        "recent_progress": ProgressUpdate.objects.filter(
            plan_item__plan__member=user
        ).order_by("-created_at")[:5],
    }


def buddy_context(user):
    return {
        "pending_plans": pending_plans(user),
        "pending_reviews": pending_reviews(user),
        "changes_requested": active_plan_items().filter(
            plan__buddy=user,
            execution_status=PlanItem.ExecutionStatus.CHANGES_REQUESTED,
        ),
        "recent_submissions": EvidenceSubmission.objects.filter(
            plan_item__plan__buddy=user
        ).order_by("-created_at")[:5],
    }


def leader_context():
    return {
        "metrics": leader_metrics(),
        "completed_items": completed_items(),
        "overdue_items": overdue_items(),
        "stale_items": stale_items(),
        "repeated_changes_items": repeated_changes_items(),
        "pending_plans": pending_plans(),
        "pending_reviews": pending_reviews(),
    }
