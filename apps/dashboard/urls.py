from django.urls import path

from . import views

app_name = "dashboard"

urlpatterns = [
    path("member/", views.member_view, name="member"),
    path("buddy/", views.buddy_view, name="buddy"),
    path("leader/", views.leader_view, name="leader"),
    path("history/", views.history_view, name="history"),
]
