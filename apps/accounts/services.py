from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.utils import timezone

from .models import Mentorship

User = get_user_model()

ROLE_ORDER = ["leader", "buddy", "member"]


def has_role(user, role_name):
    """Return True if the user belongs to the named Django group."""
    if not getattr(user, "is_authenticated", False):
        return False
    return user.groups.filter(name=role_name).exists()


def primary_role(user):
    """Return the user's highest-precedence role, or None."""
    if not getattr(user, "is_authenticated", False):
        return None
    for role in ROLE_ORDER:
        if has_role(user, role):
            return role
    return None


def visible_members_for(user):
    """Return the queryset of members visible to the given user."""
    if not getattr(user, "is_authenticated", False):
        return User.objects.none()

    if has_role(user, "leader"):
        return User.objects.filter(is_active=True, groups__name="member").distinct()

    if has_role(user, "buddy"):
        return User.objects.filter(
            mentorships_as_member__buddy=user,
            mentorships_as_member__ended_at__isnull=True,
            is_active=True,
        ).distinct()

    if has_role(user, "member"):
        return User.objects.filter(pk=user.pk)

    return User.objects.none()


def assign_buddy(member, buddy):
    """Create a new active mentorship after validating roles and state."""
    if member == buddy:
        raise ValueError("Member and Buddy cannot be the same user.")

    if not member.is_active or not buddy.is_active:
        raise ValueError("Both users must be active.")

    if not has_role(member, "member"):
        raise ValueError("The member user must have the 'member' role.")

    if not has_role(buddy, "buddy"):
        raise ValueError("The buddy user must have the 'buddy' role.")

    try:
        with transaction.atomic():
            if Mentorship.objects.filter(member=member, ended_at__isnull=True).exists():
                raise ValueError("Member already has an active Buddy relationship.")
            mentorship = Mentorship.objects.create(
                member=member,
                buddy=buddy,
                started_at=timezone.localdate(),
            )
    except IntegrityError:
        raise ValueError("Member already has an active Buddy relationship.")

    return mentorship


def set_user_active(user, is_active):
    user.is_active = bool(is_active)
    user.save(update_fields=["is_active"])
    return user


def reassign_buddy(member, new_buddy):
    if not Mentorship.objects.filter(member=member, ended_at__isnull=True).exists():
        return assign_buddy(member, new_buddy)

    with transaction.atomic():
        current = Mentorship.objects.select_for_update().get(
            member=member,
            ended_at__isnull=True,
        )
        if current.buddy_id == new_buddy.pk:
            return current
        current.ended_at = timezone.localdate()
        current.save(update_fields=["ended_at"])
        new_relationship = assign_buddy(member, new_buddy)

        from apps.learning.models import LearningCycle, LearningPlan

        LearningPlan.objects.filter(
            member=member,
            cycle__status=LearningCycle.Status.ACTIVE,
        ).exclude(status=LearningPlan.Status.ACTIVE).update(buddy=new_buddy)

    return new_relationship
