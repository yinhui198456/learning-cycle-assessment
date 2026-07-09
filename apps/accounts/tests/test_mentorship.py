import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db import IntegrityError, transaction
from django.db.models import ProtectedError
from django.utils import timezone

from apps.accounts.models import Mentorship
from apps.accounts.services import assign_buddy

User = get_user_model()


def _user(username, is_active=True):
    return User.objects.create_user(
        username=username, password="testpass123", is_active=is_active
    )


def _add_role(user, role_name):
    group = Group.objects.get(name=role_name)
    user.groups.add(group)


@pytest.mark.django_db
def test_migration_creates_all_three_groups():
    names = set(Group.objects.values_list("name", flat=True))
    assert {"member", "buddy", "leader"}.issubset(names)


@pytest.mark.django_db
def test_active_relationship_is_unique_per_member():
    member = _user("member-1")
    _add_role(member, "member")
    buddy = _user("buddy-1")
    _add_role(buddy, "buddy")

    assign_buddy(member, buddy)
    with pytest.raises(ValueError):
        assign_buddy(member, buddy)


@pytest.mark.django_db
def test_database_enforces_one_active_relationship_per_member():
    member = _user("member-2")
    _add_role(member, "member")
    buddy_one = _user("buddy-2a")
    _add_role(buddy_one, "buddy")
    buddy_two = _user("buddy-2b")
    _add_role(buddy_two, "buddy")

    Mentorship.objects.create(member=member, buddy=buddy_one)
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Mentorship.objects.create(member=member, buddy=buddy_two)


@pytest.mark.django_db
def test_same_user_cannot_be_member_and_buddy():
    member = _user("member-3")
    _add_role(member, "member")
    _add_role(member, "buddy")

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Mentorship.objects.create(member=member, buddy=member)


@pytest.mark.django_db
def test_end_date_cannot_precede_start_date():
    member = _user("member-4")
    _add_role(member, "member")
    buddy = _user("buddy-4")
    _add_role(buddy, "buddy")

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Mentorship.objects.create(
                member=member,
                buddy=buddy,
                started_at=timezone.localdate(),
                ended_at=timezone.localdate() - timezone.timedelta(days=1),
            )


@pytest.mark.django_db
def test_ended_relationship_remains_queryable_as_history():
    member = _user("member-5")
    _add_role(member, "member")
    buddy = _user("buddy-5")
    _add_role(buddy, "buddy")

    mentorship = assign_buddy(member, buddy)
    mentorship.ended_at = timezone.localdate()
    mentorship.save()

    history = Mentorship.objects.filter(member=member, ended_at__isnull=False)
    assert history.exists()


@pytest.mark.django_db
def test_ended_relationship_allows_new_active_assignment():
    member = _user("member-6")
    _add_role(member, "member")
    buddy_one = _user("buddy-6a")
    _add_role(buddy_one, "buddy")
    buddy_two = _user("buddy-6b")
    _add_role(buddy_two, "buddy")

    old = assign_buddy(member, buddy_one)
    old.ended_at = timezone.localdate()
    old.save()

    new = assign_buddy(member, buddy_two)
    assert new.buddy == buddy_two
    assert Mentorship.objects.filter(member=member, ended_at__isnull=True).count() == 1


@pytest.mark.django_db
def test_assign_buddy_rejects_wrong_roles():
    member = _user("member-7")
    _add_role(member, "member")
    leader = _user("leader-7")
    _add_role(leader, "leader")

    with pytest.raises(ValueError):
        assign_buddy(member, leader)

    only_buddy = _user("only-buddy-7")
    _add_role(only_buddy, "buddy")

    with pytest.raises(ValueError):
        assign_buddy(only_buddy, leader)


@pytest.mark.django_db
def test_assign_buddy_rejects_inactive_users():
    active_member = _user("active-member-8")
    _add_role(active_member, "member")
    inactive_member = _user("inactive-member-8", is_active=False)
    _add_role(inactive_member, "member")
    active_buddy = _user("active-buddy-8")
    _add_role(active_buddy, "buddy")
    inactive_buddy = _user("inactive-buddy-8", is_active=False)
    _add_role(inactive_buddy, "buddy")

    with pytest.raises(ValueError):
        assign_buddy(inactive_member, active_buddy)

    with pytest.raises(ValueError):
        assign_buddy(active_member, inactive_buddy)


@pytest.mark.django_db
def test_assign_buddy_rejects_same_user():
    user = _user("member-9")
    _add_role(user, "member")
    _add_role(user, "buddy")

    with pytest.raises(ValueError):
        assign_buddy(user, user)


@pytest.mark.django_db
def test_deleting_member_raises_protected_error_and_keeps_mentorship():
    member = _user("member-protected")
    _add_role(member, "member")
    buddy = _user("buddy-protected")
    _add_role(buddy, "buddy")

    mentorship = assign_buddy(member, buddy)
    pk = mentorship.pk

    with pytest.raises(ProtectedError):
        member.delete()

    assert Mentorship.objects.filter(pk=pk).exists()


@pytest.mark.django_db
def test_deleting_buddy_raises_protected_error_and_keeps_mentorship():
    member = _user("member-protected-buddy")
    _add_role(member, "member")
    buddy = _user("buddy-protected-buddy")
    _add_role(buddy, "buddy")

    mentorship = assign_buddy(member, buddy)
    pk = mentorship.pk

    with pytest.raises(ProtectedError):
        buddy.delete()

    assert Mentorship.objects.filter(pk=pk).exists()


@pytest.mark.django_db
def test_assign_buddy_raises_value_error_when_create_hits_integrity_error(
    monkeypatch,
):
    member = _user("member-race")
    _add_role(member, "member")
    buddy = _user("buddy-race")
    _add_role(buddy, "buddy")

    def _failing_create(*args, **kwargs):
        raise IntegrityError("simulated unique violation")

    monkeypatch.setattr(Mentorship.objects, "create", _failing_create)

    with pytest.raises(ValueError, match="Member already has an active Buddy relationship."):
        assign_buddy(member, buddy)
