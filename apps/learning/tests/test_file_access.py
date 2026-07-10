from http import HTTPStatus

import pytest
from django.test import Client
from django.urls import reverse

from apps.learning.models import EvidenceAttachment
from apps.learning.services_execution import submit_evidence

from .test_evidence import _upload
from .test_progress import active_plan_item, buddy, member, other_member


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


@pytest.fixture
def unrelated_client(other_member):
    client = Client()
    client.force_login(other_member)
    return client


@pytest.fixture
def evidence_attachment(active_plan_item, member):
    submit_evidence(active_plan_item, member, "done", "", [_upload()])
    return EvidenceAttachment.objects.get()


@pytest.mark.django_db
def test_unrelated_user_cannot_download_evidence(unrelated_client, evidence_attachment):
    response = unrelated_client.get(
        reverse("learning:evidence-download", args=[evidence_attachment.pk])
    )
    assert response.status_code == HTTPStatus.NOT_FOUND


@pytest.mark.django_db
def test_member_and_current_buddy_can_download_evidence(
    member_client, buddy_client, evidence_attachment
):
    url = reverse("learning:evidence-download", args=[evidence_attachment.pk])
    assert member_client.get(url).status_code == HTTPStatus.OK
    assert buddy_client.get(url).status_code == HTTPStatus.OK
