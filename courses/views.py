# courses/views.py

from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.decorators import action

from bson import ObjectId
from datetime import datetime

# Serializers
from .serializers import (
    CourseSerializer,
    EnrollmentSerializer,
    ModuleSerializer,
    TopicSerializer,
    ContentSerializer
)

# Mongo Utils
from .utils import (
    courses_collection,
    modules_collection,
    topics_collection,
    contents_collection,
    enrollment_collection,
    get_courses,
    convert_objectids,
    find_course
)

# Service Layer
from .services.enrollment_service import EnrollmentService

# Notification
from notifications.services import NotificationService


# =====================================================================
# MODULES
# =====================================================================
class ModuleViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def list(self, request):
        docs = list(modules_collection.find())
        return Response(convert_objectids(docs))

    def create(self, request):
        serializer = ModuleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        res = modules_collection.insert_one(serializer.validated_data)
        saved = modules_collection.find_one({"_id": res.inserted_id})
        return Response(convert_objectids(saved), status=201)


# =====================================================================
# TOPICS
# =====================================================================
class TopicViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def create(self, request):
        serializer = TopicSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        res = topics_collection.insert_one(serializer.validated_data)
        saved = topics_collection.find_one({"_id": res.inserted_id})
        return Response(convert_objectids(saved), status=201)


# =====================================================================
# CONTENT
# =====================================================================
class ContentViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def create(self, request):
        serializer = ContentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        res = contents_collection.insert_one(serializer.validated_data)
        saved = contents_collection.find_one({"_id": res.inserted_id})
        return Response(convert_objectids(saved), status=201)


# =====================================================================
# COURSES MAIN
# =====================================================================
class CourseViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    # ---------------------------------------------------------
    # LIST COURSES
    # ---------------------------------------------------------
    def list(self, request):
        page = int(request.GET.get("page", 1))
        limit = int(request.GET.get("limit", 10))

        extra_query = {}

        if "segment" in request.GET:
            extra_query["segment"] = {
                "$in": request.GET.get("segment").strip("[]").split(",")
            }

        if "category" in request.GET:
            extra_query["metadata.category.name"] = {
                "$in": request.GET.get("category").strip("[]").split(",")
            }

        if "sub_category" in request.GET:
            extra_query["metadata.category.sub_category.name"] = {
                "$in": request.GET.get("sub_category").strip("[]").split(",")
            }

        if "course_type" in request.GET:
            extra_query["course_type"] = {
                "$in": request.GET.get("course_type").strip("[]").split(",")
            }

        docs, total = get_courses(
            page=page,
            limit=limit,
            params=request.GET,
            extra_query=extra_query,
        )

        return Response({
            "total": total,
            "page": page,
            "limit": limit,
            "results": docs
        })

    # ---------------------------------------------------------
    # GET ONE COURSE (supports both ObjectId + string IDs)
    # ---------------------------------------------------------
    def retrieve(self, request, pk=None):

        # Try ObjectId
        try:
            doc = courses_collection.find_one({"_id": ObjectId(pk)})
            if doc:
                return Response(convert_objectids(doc))
        except:
            pass

        # Try string _id
        doc = courses_collection.find_one({"_id": pk})
        if doc:
            return Response(convert_objectids(doc))

        return Response({"detail": "Course not found"}, status=404)

    # ---------------------------------------------------------
    # CREATE COURSE
    # ---------------------------------------------------------
    def create(self, request):
        serializer = CourseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        data["created_at"] = datetime.utcnow().isoformat()
        data["updated_at"] = datetime.utcnow().isoformat()

        res = courses_collection.insert_one(data)
        saved = courses_collection.find_one({"_id": res.inserted_id})

        return Response(convert_objectids(saved), status=201)

    # ---------------------------------------------------------
    # USER SELF ENROLL
    # ---------------------------------------------------------
    @action(detail=True, methods=["post"])
    def enroll(self, request, pk=None):
        result = EnrollmentService.self_enroll(request.user, pk)

        if "error" in result:
            return Response(result, status=400)

        course_title = result["course"]["course_title"]

        # Send email
        NotificationService.send(
            event_name="COURSE_ENROLLED",
            ctx={"username": request.user.username, "course": course_title},
            to_email=request.user.email
        )

        return Response(result["enrollment"], status=201)

    # ---------------------------------------------------------
    # ADMIN ASSIGN ONE USER
    # ---------------------------------------------------------
    @action(detail=True, methods=["post"], permission_classes=[IsAdminUser])
    def assign(self, request, pk=None):

        user_id = request.data.get("user_id")
        if not user_id:
            return Response({"error": "user_id_required"}, status=400)

        from accounts.models import User
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({"error": "invalid_user"}, status=404)

        result = EnrollmentService.assign_user(user, pk)

        if "error" in result:
            return Response(result, status=400)

        course_title = result["course"]["course_title"]

        NotificationService.send(
            event_name="COURSE_ENROLLED",
            ctx={"username": user.username, "course": course_title},
            to_email=user.email
        )

        return Response(result, status=201)

    # ---------------------------------------------------------
    # ADMIN ASSIGN MULTIPLE USERS
    # ---------------------------------------------------------
    @action(
        detail=True,
        methods=["post"],
        permission_classes=[IsAdminUser],
        url_path="assign-multiple"
    )
    def assign_multiple(self, request, pk=None):

        user_ids = request.data.get("user_ids", [])

        if not isinstance(user_ids, list) or len(user_ids) == 0:
            return Response({"error": "user_ids must be a non-empty list"}, status=400)

        from accounts.models import User
        users, invalid = [], []

        for uid in user_ids:
            try:
                users.append(User.objects.get(id=uid))
            except User.DoesNotExist:
                invalid.append(uid)

        result = EnrollmentService.assign_multiple(users, pk)

        if "error" in result:
            return Response(result, status=400)

        course_title = result["course"]["course_title"]

        # Send emails to each assigned user
        for user in users:
            NotificationService.send(
                event_name="COURSE_ENROLLED",
                ctx={"username": user.username, "course": course_title},
                to_email=user.email
            )

        if invalid:
            result["invalid_user_ids"] = invalid

        return Response(result, status=201)


# =====================================================================
# ENROLLMENT VIEWSET
# =====================================================================
class EnrollmentViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def create(self, request):
        serializer = EnrollmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        course_id = serializer.validated_data["course_id"]
        result = EnrollmentService.self_enroll(request.user, course_id)
        return Response(result, status=201)

    @action(detail=False, methods=["get"])
    def my(self, request):
        user_id = str(request.user.id)
        docs = list(enrollment_collection.find({"user_id": user_id}))

        return Response({
            "username": request.user.username,
            "enrolled_courses": convert_objectids(docs)
        })
