# courses/services/enrollment_service.py
from typing import List
from django.conf import settings
from datetime import datetime

from courses import utils

class EnrollmentService:
    @staticmethod
    def self_enroll(user, course_id: str):
        """
        Called when logged-in user buys/enrolls themselves.
        Delegates to utils.enroll_user_in_course.
        """
        if not user or not getattr(user, "id", None):
            return {"error": "invalid_user", "detail": "User not authenticated or invalid"}

        return utils.enroll_user_in_course(user, course_id, status="self_enrolled")

    @staticmethod
    def assign_user(user, course_id: str, assigned_by_admin: bool = True):
        """
        Admin assignment of single user (Option C behavior).
        """
        if not user or not getattr(user, "id", None):
            return {"error": "invalid_user", "detail": "Invalid user"}

        return utils.assign_user_to_course(user, course_id)

    @staticmethod
    def assign_multiple(users: List, course_id: str):
        """
        Bulk assign list of Django User objects to a course.
        """
        if not isinstance(users, list):
            return {"error": "invalid_argument", "detail": "users must be a list"}

        return utils.assign_multiple_users_to_course(users, course_id)
