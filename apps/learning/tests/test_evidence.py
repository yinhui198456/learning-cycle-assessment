from http import HTTPStatus

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client
from django.urls import reverse

from apps.learning.models import EvidenceAttachment, EvidenceSubmission, PlanItem, ReviewDecision
from apps.learning.services_execution import (
    review_evidence,
    submit_evidence,
)

from .test_progress import active_plan_item, buddy, member
from .test_progress import other_member


@pytest.fixture
def member_client(member):
    client = Client()
    client.force_login(member)
    return client


@pytest.fixture
def buddy_client(buddy):
    client = Client()
    client.force_login(buddy)
    return client


def _upload(name="evidence.pdf", content=b"ok", content_type="application/pdf"):
    return SimpleUploadedFile(name, content, content_type=content_type)


@pytest.mark.django_db
def test_member_submits_evidence_and_buddy_approves(active_plan_item, member, buddy):
    submission = submit_evidence(
        active_plan_item,
        member,
        "finished",
        "https://example.com/result",
        [_upload()],
    )

    active_plan_item.refresh_from_db()
    assert active_plan_item.execution_status == PlanItem.ExecutionStatus.PENDING_REVIEW
    assert EvidenceSubmission.objects.count() == 1
    assert EvidenceAttachment.objects.count() == 1
    assert submission.attachments.get().original_name == "evidence.pdf"

    review_evidence(submission, buddy, ReviewDecision.Decision.COMPLETED, "ok")
    active_plan_item.refresh_from_db()
    assert active_plan_item.execution_status == PlanItem.ExecutionStatus.COMPLETED


@pytest.mark.django_db
def test_buddy_requests_changes_then_member_resubmits(active_plan_item, member, buddy):
    first = submit_evidence(active_plan_item, member, "first", "", [_upload()])
    review_evidence(first, buddy, ReviewDecision.Decision.CHANGES_REQUESTED, "needs demo")
    active_plan_item.refresh_from_db()
    assert active_plan_item.execution_status == PlanItem.ExecutionStatus.CHANGES_REQUESTED

    second = submit_evidence(active_plan_item, member, "second", "", [_upload("demo.txt", b"demo", "text/plain")])
    assert second.batch_no == 2
    active_plan_item.refresh_from_db()
    assert active_plan_item.execution_status == PlanItem.ExecutionStatus.PENDING_REVIEW


@pytest.mark.django_db
def test_request_changes_requires_comment(active_plan_item, member, buddy):
    submission = submit_evidence(active_plan_item, member, "done", "", [_upload()])

    with pytest.raises(ValueError, match="comment"):
        review_evidence(submission, buddy, ReviewDecision.Decision.CHANGES_REQUESTED, " ")


@pytest.mark.django_db
def test_evidence_file_limits(active_plan_item, member):
    too_many = [_upload(f"{index}.txt", b"x", "text/plain") for index in range(6)]
    with pytest.raises(ValueError, match="at most 5"):
        submit_evidence(active_plan_item, member, "too many", "", too_many)

    huge = _upload("huge.pdf", b"x" * (20 * 1024 * 1024 + 1), "application/pdf")
    with pytest.raises(ValueError, match="20 MB"):
        submit_evidence(active_plan_item, member, "huge", "", [huge])

    bad = _upload("bad.exe", b"x", "application/x-msdownload")
    with pytest.raises(ValueError, match="file type"):
        submit_evidence(active_plan_item, member, "bad", "", [bad])


@pytest.mark.django_db
def test_submit_and_review_evidence_views(active_plan_item, member_client, buddy_client):
    response = member_client.post(
        reverse("learning:evidence-submit", args=[active_plan_item.pk]),
        {"note": "done", "link": "", "files": [_upload()]},
    )
    assert response.status_code == HTTPStatus.FOUND
    submission = EvidenceSubmission.objects.get()

    response = buddy_client.post(
        reverse("learning:evidence-review", args=[submission.pk]),
        {"decision": ReviewDecision.Decision.COMPLETED, "comment": "ok"},
    )
    assert response.status_code == HTTPStatus.FOUND
    active_plan_item.refresh_from_db()
    assert active_plan_item.execution_status == PlanItem.ExecutionStatus.COMPLETED


@pytest.mark.django_db
def test_other_member_evidence_submit_view_returns_not_found(
    active_plan_item, other_member
):
    client = Client()
    client.force_login(other_member)

    response = client.post(
        reverse("learning:evidence-submit", args=[active_plan_item.pk]),
        {"note": "no", "link": "", "files": [_upload()]},
    )

    assert response.status_code == HTTPStatus.NOT_FOUND
