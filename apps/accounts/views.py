from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import PermissionDenied
from django.views.generic import ListView, TemplateView

from .services import has_role, primary_role, visible_members_for

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
