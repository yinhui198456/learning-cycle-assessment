from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_POST
from django.views.generic import ListView, TemplateView

from .services import (
    has_role,
    primary_role,
    reassign_buddy,
    set_user_active,
    visible_members_for,
)

User = get_user_model()


class HomeView(LoginRequiredMixin, TemplateView):
    template_name = "accounts/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context["role"] = primary_role(user)
        context["members"] = visible_members_for(user)
        return context


class UserAdminView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    template_name = "accounts/user_admin.html"
    model = User
    context_object_name = "users"

    def test_func(self):
        return has_role(self.request.user, "leader")

    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            raise PermissionDenied()
        return super().handle_no_permission()

    def get_queryset(self):
        return User.objects.order_by("username")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["buddies"] = User.objects.filter(
            is_active=True,
            groups__name="buddy",
        ).distinct()
        return context


def _require_leader(user):
    if not has_role(user, "leader"):
        raise PermissionDenied()


@login_required
@require_POST
def user_active_view(request, user_id):
    _require_leader(request.user)
    user = get_object_or_404(User, pk=user_id)
    set_user_active(user, request.POST.get("is_active") == "on")
    return redirect("user_admin")


@login_required
@require_POST
def user_buddy_view(request, user_id):
    _require_leader(request.user)
    member = get_object_or_404(User, pk=user_id)
    buddy = get_object_or_404(User, pk=request.POST.get("buddy"))
    try:
        reassign_buddy(member, buddy)
    except ValueError as exc:
        return JsonResponse({"error": str(exc)}, status=409)
    return redirect("user_admin")
