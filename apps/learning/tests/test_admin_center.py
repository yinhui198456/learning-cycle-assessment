from http import HTTPStatus

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import Client
from django.urls import reverse

from apps.learning.models import (
    CapabilityCategory,
    CapabilityDomain,
    CapabilityItem,
    LearningMaterial,
)

User = get_user_model()


def _user(username):
    return User.objects.create_user(username=username, password="testpass123")


def _add_role(user, role):
    user.groups.add(Group.objects.get(name=role))


@pytest.fixture
def leader(db):
    user = _user("leader")
    _add_role(user, "leader")
    return user


@pytest.fixture
def member(db):
    user = _user("member")
    _add_role(user, "member")
    return user


@pytest.fixture
def leader_client(leader):
    client = Client()
    client.force_login(leader)
    return client


@pytest.fixture
def member_client(member):
    client = Client()
    client.force_login(member)
    return client


@pytest.fixture
def capability(db):
    category = CapabilityCategory.objects.create(name="Tech", sort_order=1)
    l1 = CapabilityDomain.objects.create(
        category=category, code="T01", name="Backend", level=1, sort_order=1
    )
    l2 = CapabilityDomain.objects.create(
        category=category, parent=l1, code="T01.01", name="API", level=2, sort_order=1
    )
    return CapabilityItem.objects.create(
        domain=l2, code="T01.01.01", name="Old Name", sort_order=1
    )


@pytest.mark.django_db
def test_only_leader_can_access_capability_admin(member_client, leader_client, capability):
    assert member_client.get(reverse("learning:admin-capabilities")).status_code == HTTPStatus.FORBIDDEN
    response = leader_client.get(reverse("learning:admin-capabilities"))
    assert response.status_code == HTTPStatus.OK
    assert "Old Name" in response.content.decode()


@pytest.mark.django_db
def test_leader_updates_capability_and_material(leader_client, capability):
    response = leader_client.post(
        reverse("learning:admin-capability-update", args=[capability.pk]),
        {
            "name": "New Name",
            "suggested_level": "P7",
            "acceptance_method": "Review",
            "estimated_hours": "12",
            "recommended_action": "Practice",
            "is_active": "on",
        },
    )
    assert response.status_code == HTTPStatus.FOUND
    capability.refresh_from_db()
    assert capability.name == "New Name"
    assert capability.suggested_level == "P7"

    material = LearningMaterial.objects.create(code="MAT-1", name="Old Material")
    response = leader_client.post(
        reverse("learning:admin-material-update", args=[material.pk]),
        {
            "name": "New Material",
            "material_type": "book",
            "source": "wiki",
            "description": "desc",
            "status": "ready",
            "is_active": "on",
        },
    )
    assert response.status_code == HTTPStatus.FOUND
    material.refresh_from_db()
    assert material.name == "New Material"
