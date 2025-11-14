from django.urls import path
from . import views

urlpatterns = [
    path('contents/', views.ContentListCreateView.as_view()),
    path('contents/<str:content_id>/', views.ContentDetailView.as_view()),

    path('topics/', views.TopicListCreateView.as_view()),
    path('topics/<str:topic_id>/', views.TopicDetailView.as_view()),

    path('modules/', views.ModuleListCreateView.as_view()),
    path('modules/<str:module_id>/', views.ModuleDetailView.as_view()),

    path('courses/', views.CourseListCreateView.as_view()),
    path('courses/<str:course_id>/', views.CourseDetailView.as_view()),

    # FIXED
    path('enrollments/', views.EnrollmentView.as_view(), name='enrollments'),
]
