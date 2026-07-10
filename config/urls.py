from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path


# ponytail: minimal liveness probe; add DB check only if load balancer needs it

def health(request):
    return JsonResponse({"status": "ok"})


urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("django.contrib.auth.urls")),
    path("dashboard/", include("apps.dashboard.urls")),
    path("learning/", include("apps.learning.urls")),
    path("reports/", include("apps.reports.urls")),
    path("health/", health, name="health"),
    path("", include("apps.accounts.urls")),
]
