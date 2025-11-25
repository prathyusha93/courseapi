# courses/utils.py
from pymongo import MongoClient
from bson import ObjectId
from datetime import datetime
import os

# --------------------------
# Mongo connection / collections
# --------------------------
MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017/")
client = MongoClient(MONGO_URI)

# FIXED DATABASE NAME
db = client["bookdb"]

courses_collection = db["courses"]
enrollment_collection = db["enrollments"]
modules_collection = db["modules"]
topics_collection = db["topics"]
contents_collection = db["contents"]


# --------------------------
# ObjectId → String converter
# --------------------------
def convert_objectids(obj):
    if isinstance(obj, ObjectId):
        return str(obj)
    if isinstance(obj, dict):
        return {k: convert_objectids(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [convert_objectids(x) for x in obj]
    return obj


# --------------------------
# Fix for String IDs or ObjectId IDs
# --------------------------
def find_course(course_id):
    """
    Accepts both:
    - ObjectId("...")
    - "string_id"
    """

    # Try as ObjectId
    try:
        obj_id = ObjectId(course_id)
        course = courses_collection.find_one({"_id": obj_id})
        if course:
            return course
    except:
        pass

    # Try direct string match
    course = courses_collection.find_one({"_id": course_id})
    return course


# --------------------------
# Pagination
# --------------------------
def get_courses(page=1, limit=10, params=None, extra_query=None):
    if params is None:
        params = {}
    if extra_query is None:
        extra_query = {}

    skip = (page - 1) * limit
    cursor = courses_collection.find(extra_query).skip(skip).limit(limit)
    docs = [convert_objectids(d) for d in cursor]
    total = courses_collection.count_documents(extra_query)
    return docs, total


# --------------------------
# ENROLL USER
# --------------------------
# --------------------------
# ENROLL USER
# --------------------------
def enroll_user_in_course(user, course_id: str, status="self_enrolled"):

    course = find_course(course_id)
    if not course:
        return {"error": "course_not_found", "detail": "Course not found"}

    course_real_id = course["_id"]
    user_id_str = str(user.id)

    assigned_entry = {
        "id": user_id_str,
        "username": user.username
    }

    enrollment_doc = {
        "user_id": user_id_str,
        "course_id": str(course_real_id),
        "status": status,
        "created_at": datetime.utcnow().isoformat()
    }

    res = enrollment_collection.insert_one(enrollment_doc)
    saved_enrollment = enrollment_collection.find_one({"_id": res.inserted_id})

    # UPDATE course
    courses_collection.update_one(
        {"_id": course_real_id},
        {
            "$inc": {"enrollers": 1},
            "$addToSet": {"assigned_users": assigned_entry}
        }
    )

    updated = courses_collection.find_one({"_id": course_real_id})

    return {
        "course": convert_objectids(updated),
        "enrollment": convert_objectids(saved_enrollment)
    }



# --------------------------
# ASSIGN SINGLE USER
# --------------------------
# --------------------------
# ASSIGN SINGLE USER
# --------------------------
def assign_user_to_course(user, course_id: str):

    course = find_course(course_id)
    if not course:
        return {"error": "course_not_found", "detail": "Course not found"}

    course_real_id = course["_id"]
    user_id_str = str(user.id)

    assigned_entry = {
        "id": user_id_str,
        "username": user.username
    }

    enrollment_doc = {
        "user_id": user_id_str,
        "course_id": str(course_real_id),
        "status": "assigned",
        "assigned_by": "admin",
        "created_at": datetime.utcnow().isoformat()
    }

    res = enrollment_collection.insert_one(enrollment_doc)
    saved = enrollment_collection.find_one({"_id": res.inserted_id})

    courses_collection.update_one(
        {"_id": course_real_id},
        {
            "$inc": {"enrollers": 1},
            "$addToSet": {"assigned_users": assigned_entry}
        }
    )

    updated = courses_collection.find_one({"_id": course_real_id})

    return {
        "course": convert_objectids(updated),
        "enrollment": convert_objectids(saved)
    }
# --------------------------
# ASSIGN MULTIPLE USERS
# --------------------------
def assign_multiple_users_to_course(users, course_id: str):

    course = find_course(course_id)
    if not course:
        return {"error": "course_not_found", "detail": "Course not found"}

    course_real_id = course["_id"]

    all_enrollments = []
    user_ids = []
    assigned_users = []

    for user in users:
        user_id_str = str(user.id)
        user_ids.append(user_id_str)

        enrollment_doc = {
            "user_id": user_id_str,
            "username": user.username,       # ⭐ NEW
            "course_id": str(course_real_id),
            "status": "assigned",
            "created_at": datetime.utcnow().isoformat()
        }

        res = enrollment_collection.insert_one(enrollment_doc)
        saved = enrollment_collection.find_one({"_id": res.inserted_id})
        all_enrollments.append(convert_objectids(saved))

        # Add to assigned_users list (username + id)
        assigned_users.append({
            "id": user_id_str,
            "username": user.username
        })

    # Update course: increment enrollers + add list of users
    courses_collection.update_one(
        {"_id": course_real_id},
        {
            "$inc": {"enrollers": len(all_enrollments)},
            "$addToSet": {"assigned_users": {"$each": assigned_users}}
        }
    )

    updated_course = courses_collection.find_one({"_id": course_real_id})

    return {
        "course": convert_objectids(updated_course),
        "enrollments": all_enrollments
    }

