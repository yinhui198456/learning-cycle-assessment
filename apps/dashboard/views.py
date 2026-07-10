from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import render

from apps.accounts.services import has_role

from .selectors import archived_cycles, buddy_context, leader_context, member_context


def _require(user, role):
    if not has_role(user, role):
        raise PermissionDenied()


@login_required
def member_view(request):
    _require(request.user, "member")
    return render(request, "dashboard/member.html", member_context(request.user))


@login_required
def buddy_view(request):
    _require(request.user, "buddy")
    return render(request, "dashboard/buddy.html", buddy_context(request.user))


@login_required
def leader_view(request):
    _require(request.user, "leader")
    return render(request, "dashboard/leader.html", leader_context())


@login_required
def history_view(request):
    _require(request.user, "leader")
    return render(request, "dashboard/history.html", {"cycles": archived_cycles()})
