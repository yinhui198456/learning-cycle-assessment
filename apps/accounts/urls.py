from django.urls import path

from . import views

urlpatterns = [
    path("", views.HomeView.as_view(), name="home"),
    path("users/", views.UserAdminView.as_view(), name="user_admin"),
    path("users/<int:user_id>/active/", views.user_active_view, name="user_active"),
    path("users/<int:user_id>/buddy/", views.user_buddy_view, name="user_buddy"),
]
