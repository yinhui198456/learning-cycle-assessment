from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404

from apps.accounts.services import has_role
from apps.learning.models import LearningCycle

from .excel import personal_workbook, team_workbook, workbook_bytes


def _xlsx_response(workbook, filename):
    response = HttpResponse(
        workbook_bytes(workbook),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


@login_required
def personal_export_view(request, cycle_id):
    cycle = get_object_or_404(LearningCycle, pk=cycle_id)
    if not cycle.participants.filter(member=request.user).exists():
        raise Http404()
    return _xlsx_response(
        personal_workbook(request.user, cycle),
        f"personal-learning-plan-{cycle.pk}.xlsx",
    )


@login_required
def team_export_view(request, cycle_id):
    if not has_role(request.user, "leader"):
        raise PermissionDenied()
    cycle = get_object_or_404(LearningCycle, pk=cycle_id)
    return _xlsx_response(team_workbook(cycle), f"team-learning-plan-{cycle.pk}.xlsx")

