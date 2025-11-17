# courses/views.py
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from bson import ObjectId
from datetime import datetime

from .serializers import (
    ContentSerializer,
    TopicSerializer,
    ModuleSerializer,
    CourseSerializer,
    EnrollmentSerializer,
)
from .utils import (
    courses_collection,
    modules_collection,
    topics_collection,
    contents_collection,
    enrollment_collection,
    get_courses,
    convert_objectids,
)

from .services.enrollment_service import EnrollmentService


# --------------------------------------------------------
# Simple Base ViewSet for Mongo Collections
# --------------------------------------------------------
class SimpleMongoViewSet(viewsets.ViewSet):
    collection = None
    serializer_class = None
    permission_classes = [IsAuthenticated]

    def list(self, request):
        page = int(request.GET.get("page", 1))
        limit = int(request.GET.get("limit", 50))
        skip = (page - 1) * limit
        docs = list(self.collection.find().skip(skip).limit(limit))
        return Response(convert_objectids(docs))

    def retrieve(self, request, pk=None):
        try:
            doc = self.collection.find_one({"_id": ObjectId(pk)})
        except Exception:
            return Response({"detail": "Invalid ID"}, status=400)
        if not doc:
            return Response({"detail": "Not found"}, status=404)
        return Response(convert_objectids(doc))

    def create(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        res = self.collection.insert_one(serializer.validated_data)
        saved = self.collection.find_one({"_id": res.inserted_id})
        return Response(convert_objectids(saved), status=201)


class ContentViewSet(SimpleMongoViewSet):
    serializer_class = ContentSerializer
    collection = contents_collection


class TopicViewSet(SimpleMongoViewSet):
    serializer_class = TopicSerializer
    collection = topics_collection


class ModuleViewSet(SimpleMongoViewSet):
    serializer_class = ModuleSerializer
    collection = modules_collection


# --------------------------------------------------------
# Course ViewSet
# --------------------------------------------------------
class CourseViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def list(self, request):
        page = int(request.GET.get("page", 1))
        limit = int(request.GET.get("limit", 10))
        search = request.GET.get("search", "")
        sort_field = request.GET.get("sort", None)
        sort_order = request.GET.get("order", "asc")
        docs, total = get_courses(page, limit, search, sort_field, sort_order)
        return Response(
            {
                "total": total,
                "page": page,
                "limit": limit,
                "search": search,
                "sort": sort_field or "none",
                "results": docs,
            }
        )

    def retrieve(self, request, pk=None):
        try:
            doc = courses_collection.find_one({"_id": ObjectId(pk)})
        except Exception:
            return Response({"detail": "Invalid course ID"}, status=400)
        if not doc:
            return Response({"detail": "Course not found"}, status=404)
        return Response(convert_objectids(doc))

    def create(self, request):
        serializer = CourseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        data.setdefault("created_at", datetime.utcnow().isoformat())
        data.setdefault("updated_at", datetime.utcnow().isoformat())
        res = courses_collection.insert_one(data)
        saved = courses_collection.find_one({"_id": res.inserted_id})
        return Response(convert_objectids(saved), status=201)

    # ---------- self enroll ----------
    @action(detail=True, methods=["post"])
    def enroll(self, request, pk=None):
        """
        Self-enroll: the logged-in user enrolls themself.
        """
        user = request.user
        result = EnrollmentService.self_enroll(user, pk)
        if result.get("error"):
            # EnrollmentService returns {error:...} or {"ok": True...}
            return Response(result, status=400)
        return Response(result["enrollment"], status=201)

    # ---------- admin assign single ----------
    @action(detail=True, methods=["post"], url_path="assign", permission_classes=[IsAdminUser])
    def assign(self, request, pk=None):
        """
        Admin assigns a single user:
        Body: {"user_id": <int>}
        """
        user_id = request.data.get("user_id")
        if not user_id:
            return Response({"error": "user_id_required"}, status=400)

        # import here to avoid circular imports at module load
        from accounts.models import User

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({"error": "invalid_user"}, status=404)

        result = EnrollmentService.assign_user(user, pk, assigned_by_admin=True)
        if result.get("error"):
            return Response(result, status=400)
        return Response(result["enrollment"], status=201)

    # ---------- admin assign multiple ----------
    @action(detail=True, methods=["post"], url_path="assign-multiple", permission_classes=[IsAdminUser])
    def assign_multiple(self, request, pk=None):
        """
        Admin bulk-assign users:
        Body: {"user_ids": [1, 2, 3]}
        """
        user_ids = request.data.get("user_ids")
        if not isinstance(user_ids, list):
            return Response({"error": "user_ids must be a list"}, status=400)

        from accounts.models import User

        users_to_assign = []
        invalid_ids = []
        for uid in user_ids:
            try:
                u = User.objects.get(id=uid)
                users_to_assign.append(u)
            except User.DoesNotExist:
                invalid_ids.append(uid)

        service_res = EnrollmentService.assign_multiple(users_to_assign, pk)

        # if invalid_ids exist, include them in response
        if invalid_ids:
            service_res.setdefault("invalid_user_ids", invalid_ids)

        return Response(service_res, status=201 if service_res.get("ok") else 400)


# --------------------------------------------------------
# Enrollment ViewSet (simple)
# --------------------------------------------------------
class EnrollmentViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def create(self, request):
        serializer = EnrollmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        course_id = serializer.validated_data["course_id"]
        result = EnrollmentService.self_enroll(request.user, course_id)
        if result.get("error"):
            return Response(result, status=400)
        return Response(result["enrollment"], status=201)

    @action(detail=False, methods=["get"])
    def my(self, request):
        user_id = str(request.user.id)
        user_enrollments = list(enrollment_collection.find({"user_id": user_id}))
        return Response({"username": request.user.username, "enrolled_courses": convert_objectids(user_enrollments)})
