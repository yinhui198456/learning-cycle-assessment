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
]
