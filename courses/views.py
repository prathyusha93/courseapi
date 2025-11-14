# courses/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.utils import timezone
from django.conf import settings
from django.core.mail import send_mail
from bson import ObjectId
from pymongo import MongoClient

from .serializers import (
    ContentSerializer,
    TopicSerializer,
    ModuleSerializer,
    CourseSerializer,
    EnrollmentSerializer
)

# ============================
# MONGO CONNECTION
# ============================
client = MongoClient("mongodb://localhost:27017/")
db = client["bookdb"]

courses_collection = db["courses"]
modules_collection = db["modules"]
topics_collection = db["topics"]
contents_collection = db["contents"]
enrollment_collection = db["enrollments"]

# ============================
# objectid fixer
# ============================
def convert_objectids(obj):
    if isinstance(obj, ObjectId):
        return str(obj)
    if isinstance(obj, list):
        return [convert_objectids(i) for i in obj]
    if isinstance(obj, dict):
        return {k: convert_objectids(v) for k, v in obj.items()}
    return obj

# ============================
# CONTENT
# ============================
class ContentListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        docs = list(contents_collection.find())
        return Response(convert_objectids(docs), status=200)

    def post(self, request):
        serializer = ContentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        res = contents_collection.insert_one(serializer.validated_data)
        saved = contents_collection.find_one({"_id": res.inserted_id})
        return Response(convert_objectids(saved), status=201)

class ContentDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, content_id):
        try:
            doc = contents_collection.find_one({"_id": ObjectId(content_id)})
        except Exception:
            return Response({"detail": "Invalid content ID"}, status=400)
        if not doc:
            return Response({"detail": "Not found"}, status=404)
        return Response(convert_objectids(doc), status=200)

# ============================
# TOPICS
# ============================
class TopicListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        docs = list(topics_collection.find())
        return Response(convert_objectids(docs), status=200)

    def post(self, request):
        serializer = TopicSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        res = topics_collection.insert_one(serializer.validated_data)
        saved = topics_collection.find_one({"_id": res.inserted_id})
        return Response(convert_objectids(saved), status=201)

class TopicDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, topic_id):
        try:
            doc = topics_collection.find_one({"_id": ObjectId(topic_id)})
        except Exception:
            return Response({"detail": "Invalid topic ID"}, status=400)
        if not doc:
            return Response({"detail": "Not found"}, status=404)
        return Response(convert_objectids(doc), status=200)

# ============================
# MODULES
# ============================
class ModuleListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        docs = list(modules_collection.find())
        return Response(convert_objectids(docs), status=200)

    def post(self, request):
        serializer = ModuleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        res = modules_collection.insert_one(serializer.validated_data)
        saved = modules_collection.find_one({"_id": res.inserted_id})
        return Response(convert_objectids(saved), status=201)

class ModuleDetailView(APIView):
    permission_classes = [IsAuthenticated]

class CourseListCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        page = int(request.GET.get("page", 1))
        limit = int(request.GET.get("limit", 10))
        skip = (page - 1) * limit

        # ----- SEARCH -----
        search = request.GET.get("search", "").strip()

        # ----- FILTERS -----
        difficulty = request.GET.get("difficulty")
        segment = request.GET.get("segment")
        delivery_mode = request.GET.get("delivery_mode")
        min_price = request.GET.get("min_price")
        max_price = request.GET.get("max_price")

        # Build Mongo query
        query = {}

        # SEARCH IN title + description
        if search:
            query["$or"] = [
                {"course_title": {"$regex": search, "$options": "i"}},
                {"course_description": {"$regex": search, "$options": "i"}},
            ]

        # FILTER: difficulty
        if difficulty:
            query["metadata.difficulty_level"] = difficulty

        # FILTER: segment
        if segment:
            query["metadata.segment"] = segment

        # FILTER: delivery mode
        if delivery_mode:
            query["metadata.delivery_mode"] = delivery_mode

        # FILTER: price range
        price_filter = {}
        if min_price:
            price_filter["$gte"] = int(min_price)
        if max_price:
            price_filter["$lte"] = int(max_price)

        if price_filter:
            query["display_price.amount"] = price_filter

        # Total Before Pagination
        total = courses_collection.count_documents(query)

        # Fetch with pagination
        docs = list(
            courses_collection.find(query)
            .skip(skip)
            .limit(limit)
            .sort("_id", -1)
        )

        return Response({
            "total": total,
            "page": page,
            "limit": limit,
            "filters": {
                "search": search,
                "difficulty": difficulty,
                "segment": segment,
                "delivery_mode": delivery_mode,
                "min_price": min_price,
                "max_price": max_price
            },
            "results": convert_objectids(docs)
        }, status=200)



    def post(self, request):
        # Posting a course should be authenticated (as above)
        serializer = CourseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        now = timezone.now().isoformat()
        data = serializer.validated_data
        data["created_at"] = now
        data["updated_at"] = now
        # ensure enrollers and enrolled_users fields exist
        data.setdefault("enrollers", 0)
        data.setdefault("enrolled_users", [])
        res = courses_collection.insert_one(data)
        saved = courses_collection.find_one({"_id": res.inserted_id})
        return Response(convert_objectids(saved), status=201)

class CourseDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, course_id):
        try:
            doc = courses_collection.find_one({"_id": ObjectId(course_id)})
        except Exception:
            return Response({"detail": "Invalid ID"}, status=400)
        if not doc:
            return Response({"detail": "Course not found"}, status=404)
        return Response(convert_objectids(doc), status=200)

# ============================
# ENROLLMENTS
# ============================
class EnrollmentView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = EnrollmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        course_id = serializer.validated_data["course_id"]

        user_id = str(request.user.id)
        username = request.user.username
        email = request.user.email or ""

        # validate course
        try:
            course = courses_collection.find_one({"_id": ObjectId(course_id)})
        except Exception:
            return Response({"detail": "Invalid course id"}, status=400)
        if not course:
            return Response({"detail": "Course not found"}, status=404)

        # avoid duplicate enrollment
        existing = enrollment_collection.find_one({
            "course_id": ObjectId(course_id),
            "user_id": user_id
        })
        if existing:
            return Response({"detail": "User already enrolled"}, status=400)

        price = course.get("display_price", {}).get("amount", 0)
        course_title = course.get("course_title", "Course")

        doc = {
            "user_id": user_id,
            "username": username,
            "course_id": ObjectId(course_id),
            "price": price,
            "status": "enrolled",
            "enrolled_at": timezone.now().isoformat()
        }

        res = enrollment_collection.insert_one(doc)
        saved = enrollment_collection.find_one({"_id": res.inserted_id})

        # increment enrollers and add enrolled user into set
        try:
            courses_collection.update_one(
                {"_id": ObjectId(course_id)},
                {
                    "$inc": {"enrollers": 1},
                    # store minimal user info. $addToSet prevents duplicates.
                    "$addToSet": {"enrolled_users": {"id": user_id, "username": username}}
                }
            )
        except Exception as e:
            print("Course update failed:", e)

        # send confirmation email if present
        email_sent = False
        if email:
            subject = "Course Enrollment Confirmation"
            message = f"""Hi {username},

You have successfully enrolled in:

Course: {course_title}
Price: ₹{price}
Date: {timezone.now().strftime('%Y-%m-%d %H:%M')}

Thank you!
- Synchroni Academy
"""
            try:
                send_mail(
                    subject,
                    message,
                    settings.DEFAULT_FROM_EMAIL,
                    [email],
                    fail_silently=False
                )
                email_sent = True
            except Exception as e:
                print("Email sending failed:", e)
                email_sent = False

        result = convert_objectids(saved)
        result["email_sent"] = email_sent
        return Response(result, status=201)
