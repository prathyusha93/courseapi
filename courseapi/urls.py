from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

urlpatterns = [
    path("admin/", admin.site.urls),

    path("api/", include("courses.urls")),
    path("api/auth/", include("accounts.urls")),      # API URLS
    path("auth/", include("accounts.frontend_urls")), # HTML FORM URLS

    path("api/auth/token/", TokenObtainPairView.as_view()),
    path("api/auth/token/refresh/", TokenRefreshView.as_view()),
]
