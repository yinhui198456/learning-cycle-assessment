import os

from django.contrib.auth import get_user_model
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.accounts.models import Mentorship
from apps.learning.models import (
    Assessment,
    CycleParticipant,
    EvidenceAttachment,
    EvidenceSubmission,
    LearningCycle,
    LearningPlan,
    PlanApprovalEvent,
    PlanItem,
    ProgressUpdate,
    ReviewDecision,
)

User = get_user_model()


def _env_or_default(prefix, default):
    return os.environ.get(prefix, default)


class Command(BaseCommand):
    help = "Delete smoke-test data created by the journey loop for configured users."

    def add_arguments(self, parser):
        parser.add_argument(
            "--member",
            default=_env_or_default("SMOKE_MEMBER_USER", "smoke_member"),
            help="Smoke member username (env: SMOKE_MEMBER_USER).",
        )
        parser.add_argument(
            "--buddy",
            default=_env_or_default("SMOKE_BUDDY_USER", "smoke_buddy"),
            help="Smoke buddy username (env: SMOKE_BUDDY_USER).",
        )
        parser.add_argument(
            "--leader",
            default=_env_or_default("SMOKE_LEADER_USER", "smoke_leader"),
            help="Smoke leader username (env: SMOKE_LEADER_USER).",
        )

    def handle(self, *args, **options):
        member = User.objects.filter(username=options["member"]).first()
        leader = User.objects.filter(username=options["leader"]).first()

        if not member:
            self.stdout.write(self.style.NOTICE("Smoke member does not exist; nothing to clean."))
            return

        deleted = {}

        with transaction.atomic():
            # Plans and items owned by the smoke member.
            member_plan_ids = list(
                LearningPlan.objects.filter(member=member).values_list("pk", flat=True)
            )

            # Evidence review decisions made by the smoke buddy.
            review_ids = list(
                ReviewDecision.objects.filter(
                    submission__plan_item__plan_id__in=member_plan_ids
                ).values_list("pk", flat=True)
            )
            deleted["review_decisions"], _ = ReviewDecision.objects.filter(
                pk__in=review_ids
            ).delete()

            # Evidence submissions from the member; delete files first.
            submission_ids = list(
                EvidenceSubmission.objects.filter(
                    plan_item__plan_id__in=member_plan_ids
                ).values_list("pk", flat=True)
            )
            attachment_count = 0
            for attachment in EvidenceAttachment.objects.filter(
                submission_id__in=submission_ids
            ):
                if attachment.file:
                    try:
                        default_storage.delete(attachment.file.name)
                        attachment_count += 1
                    except Exception as exc:  # pragma: no cover - best effort cleanup
                        self.stderr.write(f"Could not delete file {attachment.file.name}: {exc}")
            EvidenceAttachment.objects.filter(submission_id__in=submission_ids).delete()
            deleted["evidence_attachments"] = attachment_count

            # Cascades progress, guidance, evidence submissions, approval events.
            deleted["plans"], _ = LearningPlan.objects.filter(member=member).delete()

            # Assessments and participation.
            deleted["assessments"], _ = Assessment.objects.filter(member=member).delete()
            deleted["cycle_participants"], _ = CycleParticipant.objects.filter(
                member=member
            ).delete()

            # Cycles created by the smoke leader that no longer have participants.
            if leader:
                empty_cycle_ids = list(
                    LearningCycle.objects.filter(
                        created_by=leader, participants__isnull=True
                    ).values_list("pk", flat=True)
                )
                deleted["cycles"], _ = LearningCycle.objects.filter(
                    pk__in=empty_cycle_ids
                ).delete()

            # Remove the active mentorship so create_smoke_journey can recreate it.
            deleted["mentorships"], _ = Mentorship.objects.filter(
                member=member, ended_at__isnull=True
            ).delete()

        summary = ", ".join(f"{k}={v}" for k, v in deleted.items())
        self.stdout.write(self.style.SUCCESS(f"smoke journey cleaned: {summary}"))
