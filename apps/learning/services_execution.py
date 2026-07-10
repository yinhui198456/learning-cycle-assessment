from decimal import Decimal

from django.db import transaction

from apps.accounts.models import Mentorship
from apps.accounts.services import has_role

from .models import (
    EvidenceAttachment,
    EvidenceSubmission,
    GuidanceComment,
    LearningPlan,
    PlanItem,
    ProgressUpdate,
    ReviewDecision,
)

MAX_FILES = 5
MAX_FILE_SIZE = 20 * 1024 * 1024
ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "image/png",
    "image/jpeg",
    "text/plain",
    "application/zip",
}


def _is_current_buddy(plan, user):
    return plan.buddy_id == user.pk and Mentorship.objects.filter(
        member=plan.member,
        buddy=user,
        ended_at__isnull=True,
    ).exists()


def _require_member_item(plan_item, user):
    if plan_item.plan.member_id != user.pk:
        raise PermissionError("Only the member can update this item.")
    if plan_item.plan.status != LearningPlan.Status.ACTIVE:
        raise ValueError("Plan must be active.")


def _require_buddy_item(plan_item, user):
    if not _is_current_buddy(plan_item.plan, user):
        raise PermissionError("Only the current Buddy can update this item.")


def add_progress_update(plan_item, actor, content, hours_spent):
    _require_member_item(plan_item, actor)
    if plan_item.execution_status == PlanItem.ExecutionStatus.COMPLETED:
        raise ValueError("Completed items cannot be updated.")
    if not content.strip():
        raise ValueError("Progress content is required.")
    hours = Decimal(str(hours_spent))
    if hours <= 0:
        raise ValueError("Hours must be positive.")
    return ProgressUpdate.objects.create(
        plan_item=plan_item,
        author=actor,
        content=content.strip(),
        hours_spent=hours,
    )


def add_guidance_comment(plan_item, actor, content):
    _require_buddy_item(plan_item, actor)
    if not content.strip():
        raise ValueError("Comment content is required.")
    return GuidanceComment.objects.create(
        plan_item=plan_item,
        author=actor,
        content=content.strip(),
    )


def _validate_files(files):
    if len(files) > MAX_FILES:
        raise ValueError("Submit at most 5 files.")
    for uploaded in files:
        if uploaded.size > MAX_FILE_SIZE:
            raise ValueError("Each file must be 20 MB or smaller.")
        if getattr(uploaded, "content_type", "") not in ALLOWED_CONTENT_TYPES:
            raise ValueError("Unsupported file type.")


def submit_evidence(plan_item, actor, note, link, files):
    _require_member_item(plan_item, actor)
    if plan_item.execution_status not in (
        PlanItem.ExecutionStatus.WORKING,
        PlanItem.ExecutionStatus.CHANGES_REQUESTED,
    ):
        raise ValueError("Evidence cannot be submitted in the current status.")
    files = list(files)
    _validate_files(files)

    with transaction.atomic():
        batch_no = plan_item.evidence_submissions.count() + 1
        submission = EvidenceSubmission.objects.create(
            plan_item=plan_item,
            submitted_by=actor,
            note=note.strip(),
            link=link.strip(),
            batch_no=batch_no,
        )
        for uploaded in files:
            EvidenceAttachment.objects.create(
                submission=submission,
                file=uploaded,
                original_name=uploaded.name,
                content_type=getattr(uploaded, "content_type", ""),
                size_bytes=uploaded.size,
            )
        plan_item.execution_status = PlanItem.ExecutionStatus.PENDING_REVIEW
        plan_item.save(update_fields=["execution_status", "updated_at"])
    return submission


def review_evidence(submission, actor, decision, comment):
    plan_item = submission.plan_item
    _require_buddy_item(plan_item, actor)
    if plan_item.execution_status != PlanItem.ExecutionStatus.PENDING_REVIEW:
        raise ValueError("Evidence is not pending review.")
    if decision == ReviewDecision.Decision.CHANGES_REQUESTED and not comment.strip():
        raise ValueError("A comment is required to request changes.")

    ReviewDecision.objects.create(
        submission=submission,
        reviewer=actor,
        decision=decision,
        comment=comment.strip(),
    )
    if decision == ReviewDecision.Decision.COMPLETED:
        plan_item.execution_status = PlanItem.ExecutionStatus.COMPLETED
    elif decision == ReviewDecision.Decision.CHANGES_REQUESTED:
        plan_item.execution_status = PlanItem.ExecutionStatus.CHANGES_REQUESTED
    else:
        raise ValueError("Invalid review decision.")
    plan_item.save(update_fields=["execution_status", "updated_at"])
    return submission


def can_download_attachment(user, attachment):
    plan = attachment.submission.plan_item.plan
    return (
        plan.member_id == user.pk
        or _is_current_buddy(plan, user)
        or has_role(user, "leader")
    )
