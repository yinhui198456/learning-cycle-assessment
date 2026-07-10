import json
from http import HTTPStatus

from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View
from django.views.decorators.http import require_POST

from apps.accounts.services import has_role, primary_role

from .forms import LearningCycleForm
from .models import Assessment, CapabilityCategory, LearningCycle
from .services import (
    assessment_counts,
    ensure_assessments_for_cycle,
    get_member_current_cycle,
    save_single_assessment,
    update_assessments_batch,
)


class LeaderRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        return has_role(self.request.user, "leader")

    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            from django.core.exceptions import PermissionDenied

            raise PermissionDenied()
        return super().handle_no_permission()


class CycleAdminView(LeaderRequiredMixin, View):
    template_name = "learning/cycle_admin.html"

    def get(self, request, *args, **kwargs):
        form = LearningCycleForm()
        cycles = LearningCycle.objects.order_by("-start_date")
        return render(
            request,
            self.template_name,
            {
                "form": form,
                "cycles": cycles,
                "role": primary_role(request.user),
            },
        )

    def post(self, request, *args, **kwargs):
        form = LearningCycleForm(request.POST)
        if form.is_valid():
            form.create_cycle(created_by=request.user)
            return redirect("learning:cycle_admin")
        cycles = LearningCycle.objects.order_by("-start_date")
        return render(
            request,
            self.template_name,
            {
                "form": form,
                "cycles": cycles,
                "role": primary_role(request.user),
            },
        )


cycle_admin_view = CycleAdminView.as_view()


def _parse_json_body(request):
    """Return (payload, None) or (None, JsonResponse) for malformed input."""
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None, JsonResponse(
            {"errors": {"__all__": ["请求必须是有效的 JSON。"]}},
            status=HTTPStatus.BAD_REQUEST,
        )
    if not isinstance(payload, dict):
        return None, JsonResponse(
            {"errors": {"__all__": ["请求必须是 JSON 对象。"]}},
            status=HTTPStatus.BAD_REQUEST,
        )
    return payload, None


@login_required
def assessment_view(request):
    if not has_role(request.user, "member"):
        from django.core.exceptions import PermissionDenied

        raise PermissionDenied()

    cycle_id = request.GET.get("cycle")
    if cycle_id:
        cycle = get_object_or_404(
            LearningCycle,
            pk=cycle_id,
            status=LearningCycle.Status.ACTIVE,
            participants__member=request.user,
        )
    else:
        cycle = get_member_current_cycle(request.user)

    if cycle is None:
        return render(
            request,
            "learning/assessment.html",
            {
                "cycle": None,
                "rows": [],
                "counts": {"total": 0, "assessed": 0, "included": 0},
            },
        )

    ensure_assessments_for_cycle(cycle, request.user)

    categories = (
        CapabilityCategory.objects.filter(is_active=True)
        .prefetch_related(
            "domains",
            "domains__children",
            "domains__children__items",
        )
        .order_by("sort_order", "name")
    )

    assessments = {
        a.capability_item_id: a
        for a in Assessment.objects.filter(
            cycle=cycle, member=request.user
        ).select_related("capability_item__domain__parent__category")
    }

    rows = []
    for category in categories:
        l1_domains = [d for d in category.domains.all() if d.level == 1 and d.is_active]
        for l1 in l1_domains:
            l2_domains = [
                d for d in l1.children.all() if d.level == 2 and d.is_active
            ]
            for l2 in l2_domains:
                items = [i for i in l2.items.all() if i.is_active]
                for item in items:
                    rows.append(
                        {
                            "category": category,
                            "l1": l1,
                            "l2": l2,
                            "item": item,
                            "assessment": assessments.get(item.pk),
                        }
                    )

    counts = assessment_counts(cycle, request.user)

    return render(
        request,
        "learning/assessment.html",
        {
            "cycle": cycle,
            "rows": rows,
            "counts": counts,
        },
    )


@login_required
@require_POST
def assessment_save_view(request, assessment_id):
    if not has_role(request.user, "member"):
        return JsonResponse({"error": "forbidden"}, status=HTTPStatus.FORBIDDEN)

    assessment = get_object_or_404(
        Assessment,
        pk=assessment_id,
        member=request.user,
    )

    payload, error_response = _parse_json_body(request)
    if error_response:
        return error_response

    allowed = {
        "current_level",
        "target_level",
        "priority",
        "included",
        "planned_quarter",
        "planned_month",
        "version",
    }
    data = {key: payload[key] for key in allowed if key in payload}

    result = save_single_assessment(assessment, data)
    if result["ok"]:
        result["counts"] = assessment_counts(assessment.cycle, request.user)
        return JsonResponse(result)
    return JsonResponse(result, status=result["status"])


@login_required
@require_POST
def assessment_batch_view(request):
    if not has_role(request.user, "member"):
        return JsonResponse({"error": "forbidden"}, status=HTTPStatus.FORBIDDEN)

    payload, error_response = _parse_json_body(request)
    if error_response:
        return error_response

    ids = payload.get("ids", [])
    if not isinstance(ids, list):
        return JsonResponse(
            {"errors": {"ids": ["ids 必须是列表。"]}},
            status=HTTPStatus.BAD_REQUEST,
        )
    if not ids:
        return JsonResponse({"ok": True, "updated": 0})

    data = {}
    for field in ("priority", "included", "planned_quarter", "planned_month"):
        if field in payload:
            data[field] = payload[field]

    result = update_assessments_batch(request.user, ids, data)
    if result["ok"]:
        cycle = LearningCycle.objects.get(pk=result.get("cycle_id"))
        result["counts"] = assessment_counts(cycle, request.user)
        return JsonResponse(result)
    return JsonResponse(result, status=result["status"])
