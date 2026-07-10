from django.urls import path

from . import views

app_name = "reports"

urlpatterns = [
    path("personal/<int:cycle_id>/", views.personal_export_view, name="personal"),
    path("team/<int:cycle_id>/", views.team_export_view, name="team"),
]

