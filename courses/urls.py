# courses/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    CourseViewSet,
    ModuleViewSet,
    TopicViewSet,
    ContentViewSet,
    EnrollmentViewSet,
)

router = DefaultRouter()
router.register(r"courses", CourseViewSet, basename="course")
router.register(r"modules", ModuleViewSet, basename="module")
router.register(r"topics", TopicViewSet, basename="topic")
router.register(r"contents", ContentViewSet, basename="content")
router.register(r"enrollments", EnrollmentViewSet, basename="enrollment")

urlpatterns = [
    path("", include(router.urls)),   # prefix handled by project urls (api/)
]
