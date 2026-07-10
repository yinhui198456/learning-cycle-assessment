from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("django.contrib.auth.urls")),
    path("dashboard/", include("apps.dashboard.urls")),
    path("learning/", include("apps.learning.urls")),
    path("", include("apps.accounts.urls")),
]
