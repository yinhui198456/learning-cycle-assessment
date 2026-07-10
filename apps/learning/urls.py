from django.urls import path

from . import views

app_name = "learning"

urlpatterns = [
    path("cycles/", views.cycle_admin_view, name="cycle_admin"),
    path("assessment/", views.assessment_view, name="assessment"),
    path(
        "assessment/<int:assessment_id>/save/",
        views.assessment_save_view,
        name="assessment-save",
    ),
    path("assessment/batch/", views.assessment_batch_view, name="assessment-batch"),
    path("plans/<int:plan_id>/", views.plan_detail_view, name="plan-detail"),
    path(
        "cycles/<int:cycle_id>/plan/generate/",
        views.plan_generate_view,
        name="plan-generate",
    ),
    path("plans/<int:plan_id>/submit/", views.plan_submit_view, name="plan-submit"),
    path(
        "plan-items/<int:item_id>/edit/",
        views.plan_item_edit_view,
        name="plan-item-edit",
    ),
    path("buddy/approvals/", views.buddy_approvals_view, name="buddy-approvals"),
    path("plans/<int:plan_id>/approve/", views.plan_approve_view, name="plan-approve"),
    path(
        "plans/<int:plan_id>/request-changes/",
        views.plan_request_changes_view,
        name="plan-request-changes",
    ),
]
