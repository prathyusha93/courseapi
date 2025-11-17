# courses/services/enrollment_service.py
"""
EnrollmentService
- centralizes all enrollment logic
- used by views for single or bulk assignment/enrollment
"""

from datetime import datetime
from typing import Dict, List, Tuple, Any

from bson import ObjectId

from ..utils import (
    courses_collection,
    enrollment_collection,
    convert_objectids,
)

# NOTE: Importing Django's User inside functions avoids circular import
# and ensures this module can be imported by management commands/tests.


class EnrollmentService:
    @staticmethod
    def _to_str_id(v: Any) -> str:
        return str(v)

    @staticmethod
    def validate_course(course_id: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Validate and return (ok, course or error dict).
        """
        try:
            course_obj_id = ObjectId(course_id)
        except Exception:
            return False, {"error": "invalid_course", "detail": "Invalid course id"}

        course = courses_collection.find_one({"_id": course_obj_id})
        if not course:
            return False, {"error": "course_not_found", "detail": "Course not found"}

        return True, course

    @staticmethod
    def _already_enrolled(course_id: str, user_id: str) -> bool:
        return enrollment_collection.find_one({"course_id": course_id, "user_id": user_id}) is not None

    @staticmethod
    def assign_user(user_obj, course_id: str, assigned_by_admin: bool = True) -> Dict[str, Any]:
        """
        Assigns a single user to a course (admin assignment or programmatic).
        Returns dict: either enrollment doc or error dict.
        """
        user_id = EnrollmentService._to_str_id(user_obj.id)
        username = getattr(user_obj, "username", "")

        # validate course
        ok, course_or_err = EnrollmentService.validate_course(course_id)
        if not ok:
            return course_or_err

        if EnrollmentService._already_enrolled(course_id, user_id):
            return {"error": "already_enrolled", "detail": "User already enrolled"}

        # create enrollment document
        doc = {
            "user_id": user_id,
            "username": username,
            "course_id": course_id,
            "status": "assigned_by_admin" if assigned_by_admin else "self_enrolled",
            "enrolled_at": datetime.utcnow().isoformat(),
        }

        res = enrollment_collection.insert_one(doc)
        saved = enrollment_collection.find_one({"_id": res.inserted_id})

        # update course counters and list
        try:
            courses_collection.update_one(
                {"_id": ObjectId(course_id)},
                {
                    "$inc": {"enrollers": 1},
                    "$addToSet": {"enrolled_users": {"user_id": user_id, "username": username}},
                },
            )
        except Exception:
            # best-effort update; ignore failure but still return saved enrollment
            pass

        result = convert_objectids(saved)
        return {"ok": True, "enrollment": result}

    @staticmethod
    def self_enroll(user_obj, course_id: str) -> Dict[str, Any]:
        # wrapper for self enrollment (assigned_by_admin=False)
        return EnrollmentService.assign_user(user_obj, course_id, assigned_by_admin=False)

    @staticmethod
    def assign_multiple(user_objs: List[Any], course_id: str) -> Dict[str, Any]:
        """
        Assign a list of Django User objects to a course.
        Returns summary:
          { "assigned": [...], "skipped": [...], "course_id": course_id }
        """
        ok, course_or_err = EnrollmentService.validate_course(course_id)
        if not ok:
            return course_or_err

        assigned = []
        skipped = []

        for user in user_objs:
            user_id = EnrollmentService._to_str_id(user.id)
            if EnrollmentService._already_enrolled(course_id, user_id):
                skipped.append({"id": user_id, "username": user.username, "reason": "already_enrolled"})
                continue

            res = EnrollmentService.assign_user(user, course_id, assigned_by_admin=True)
            if res.get("ok"):
                assigned.append({"id": user_id, "username": user.username})
            else:
                # collect any error
                reason = res.get("error", res.get("detail", "unknown"))
                skipped.append({"id": user_id, "username": user.username, "reason": reason})

        return {"ok": True, "course_id": course_id, "assigned": assigned, "skipped": skipped}
