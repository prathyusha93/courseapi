# courses/utils.py
from pymongo import MongoClient
from bson import ObjectId
from typing import List, Tuple, Any, Dict
from datetime import datetime
from django.conf import settings
from django.core.mail import send_mail

# ---------------------------
# Mongo connection + collections
# ---------------------------
client = MongoClient("mongodb://localhost:27017/")
db = client.get_database("bookdb")

courses_collection = db["courses"]
modules_collection = db["modules"]
topics_collection = db["topics"]
contents_collection = db["contents"]
enrollment_collection = db["enrollments"]

# ---------------------------
# Convert ObjectId -> str recursively
# ---------------------------
def convert_objectids(obj: Any) -> Any:
    if isinstance(obj, ObjectId):
        return str(obj)
    if isinstance(obj, list):
        return [convert_objectids(i) for i in obj]
    if isinstance(obj, dict):
        return {k: convert_objectids(v) for k, v in obj.items()}
    return obj

# ---------------------------
# Field filtering helper
# Accept "display_price.amount", "metadata.category.sub_category", etc.
# ---------------------------
def filter_fields(document: dict, requested_fields: List[str]) -> dict:
    if not requested_fields:
        return document

    filtered: dict = {}
    for field in requested_fields:
        parts = field.split(".")
        value = document
        valid = True
        for p in parts:
            if isinstance(value, dict) and p in value:
                value = value[p]
            else:
                valid = False
                break
        if not valid:
            continue
        # build nested structure in filtered
        cur = filtered
        for i, p in enumerate(parts):
            if i == len(parts) - 1:
                cur[p] = value
            else:
                cur = cur.setdefault(p, {})
    return filtered

# ---------------------------
# Field alias map (user friendly)
# ---------------------------
FIELD_ALIAS_MAP = {
    "amount": "display_price.amount",
    "segment": "segment",  # after normalization we add top-level 'segment' if needed
    "sub_category": "sub_category",  # flattened below
    "category": "category",
    "tags": "tags",
    "mode": "mode",
    "created_by": "created_by",
    "created_at": "metadata.created_at",
    "updated_by": "updated_by",
    "updated_at": "metadata.updated_at",
}

def normalize_requested_fields(fields: List[str]) -> List[str]:
    normalized = []
    for f in fields:
        f = f.strip()
        if not f:
            continue
        mapped = FIELD_ALIAS_MAP.get(f, f)
        normalized.append(mapped)
    return normalized

# ---------------------------
# Build search query
# ---------------------------
def build_query(search: str = "", extra_query: dict = None) -> dict:
    q: dict = {}
    if search:
        q["$or"] = [
            {"course_title": {"$regex": search, "$options": "i"}},
            {"course_description": {"$regex": search, "$options": "i"}},
        ]
    if extra_query:
        for k, v in extra_query.items():
            q[k] = v
    return q

# ---------------------------
# normalize docs: add top-level 'segment' if exist in metadata
# and flatten metadata fields (sub_category, category, tags, mode, created_by, updated_by)
# ---------------------------
def flatten_metadata(docs: List[dict]) -> None:
    for d in docs:
        meta = d.get("metadata", {}) or {}
        # sub_category: metadata.category.sub_category -> top-level sub_category
        try:
            if isinstance(meta.get("category"), dict) and meta["category"].get("sub_category"):
                d["sub_category"] = meta["category"]["sub_category"]
        except Exception:
            pass
        # category
        try:
            if meta.get("category"):
                d["category"] = meta["category"]
        except Exception:
            pass
        # tags
        try:
            if meta.get("tags") is not None:
                d["tags"] = meta["tags"]
        except Exception:
            pass
        # mode
        try:
            if meta.get("mode") is not None:
                d["mode"] = meta["mode"]
        except Exception:
            pass
        # created_by / updated_by
        try:
            if meta.get("created_by") is not None:
                d["created_by"] = meta["created_by"]
        except Exception:
            pass
        try:
            if meta.get("updated_by") is not None:
                d["updated_by"] = meta["updated_by"]
        except Exception:
            pass
        # segment normalization
        try:
            if not d.get("segment") and meta.get("segment"):
                d["segment"] = meta.get("segment")
        except Exception:
            pass
        # remove metadata completely to avoid nested responses when user asked top-level fields only
        # (we keep it if clients requested it explicitly in fields)
        # We'll remove only if the document contains metadata and top-level fields were created
        if "metadata" in d:
            # do not delete metadata if client requested metadata explicitly (handled later by filter_fields)
            # For now keep metadata; view/get_courses may delete it after field-selection
            pass

# ---------------------------
# Get courses (pagination + search + sorting + field selection)
# ---------------------------
def get_courses(
    page: int = 1,
    limit: int = 10,
    search: str = "",
    sort_field: str | None = None,
    sort_order: str = "asc",
    fields: List[str] | None = None,
) -> Tuple[List[dict], int]:
    skip = (page - 1) * limit
    sort_dir = 1 if sort_order == "asc" else -1
    query = build_query(search)

    allowed_sort = {
        "course_title": "course_title",
        "display_price.amount": "display_price.amount",
        "amount": "display_price.amount",
        "course_start_date": "course_start_date",
        "course_end_date": "course_end_date",
        # 'segment' handled separately via aggregation that picks top-level or metadata.segment
    }

    docs = []
    # Date sorting -> aggregation converts string ➜ date
    if sort_field in ("course_start_date", "course_end_date"):
        pipeline = [
            {"$match": query},
            {"$addFields": {"_sort_date": {"$toDate": f"${sort_field}"}}},
            {"$sort": {"_sort_date": sort_dir}},
            {"$skip": skip},
            {"$limit": limit},
        ]
        docs = list(courses_collection.aggregate(pipeline))
    elif sort_field == "segment":
        # create sort_segment field which prefers top-level segment then metadata.segment
        pipeline = [
            {"$match": query},
            {"$addFields": {"sort_segment": {"$ifNull": ["$segment", "$metadata.segment"]}}},
            {"$sort": {"sort_segment": sort_dir}},
            {"$skip": skip},
            {"$limit": limit},
        ]
        docs = list(courses_collection.aggregate(pipeline))
    elif sort_field in allowed_sort:
        real_field = allowed_sort.get(sort_field)
        docs = list(
            courses_collection.find(query)
            .sort(real_field, sort_dir)
            .skip(skip)
            .limit(limit)
        )
    else:
        docs = list(
            courses_collection.find(query)
            .sort("created_at", -1)
            .skip(skip)
            .limit(limit)
        )

    total = courses_collection.count_documents(query)

    # Flatten helpful metadata fields to top-level (so user can request "sub_category", "segment", etc.)
    flatten_metadata(docs)

    # Field selection: normalize aliases and pick fields
    if fields:
        requested = normalize_requested_fields(fields)
        # If user asked for a top-level alias (like sub_category), the mapping already returns 'sub_category'
        docs = [filter_fields(doc, requested) for doc in docs]
    else:
        # If no fields param, remove metadata if we've flattened the necessary fields to keep response tidy.
        # Keep metadata only if client requested it explicitly in fields; otherwise remove to reduce payload.
        for d in docs:
            if "metadata" in d:
                d.pop("metadata", None)

    docs = [convert_objectids(d) for d in docs]
    return docs, total

# ---------------------------
# Enrollment helper
# returns dict (enrollment_doc + email_sent flag)
# ---------------------------
def enroll_user(user_id: str, course_id: str) -> Dict[str, Any]:

    # find the user in Django DB
    from accounts.models import User
    try:
        user_obj = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return {"error": "user_not_found", "detail": "User does not exist"}

    username = user_obj.username
    email = user_obj.email

    # validate course
    try:
        course_obj_id = ObjectId(course_id)
    except Exception:
        return {"error": "invalid_course_id"}

    course = courses_collection.find_one({"_id": course_obj_id})
    if not course:
        return {"error": "course_not_found"}

    # check duplicate enrollment
    existing = enrollment_collection.find_one({
        "course_id": course_id,
        "user_id": user_id
    })
    if existing:
        return {"error": "already_enrolled"}

    # get price
    price = course.get("display_price", {}).get("amount", 0)

    # insert enrollment
    doc = {
        "user_id": user_id,
        "username": username,
        "course_id": course_id,
        "price": price,
        "status": "enrolled",
        "enrolled_at": datetime.utcnow().isoformat()
    }
    res = enrollment_collection.insert_one(doc)

    # update course
    courses_collection.update_one(
        {"_id": course_obj_id},
        {
            "$inc": {"enrollers": 1},
            "$addToSet": {"enrolled_users": {"user_id": user_id, "username": username}}
        }
    )

    saved = enrollment_collection.find_one({"_id": res.inserted_id})
    return {"ok": True, "enrollment": convert_objectids(saved)}

    # ------------------------------
    # 🔥 UPDATE COURSE DOCUMENT
    # ------------------------------
    try:
        courses_collection.update_one(
            {"_id": course_obj_id},
            {
                "$inc": {"enrollers": 1},
                "$addToSet": {
                    "enrolled_users": {
                        "user_id": user_id,
                        "username": username
                    }
                }
            }
        )
    except Exception:
        pass

    # ------------------------------
    # 🔥 SEND EMAIL (if available)
    # ------------------------------
    email_sent = False

    if email:
        try:
            subject = "Course Enrollment Confirmation"
            message = (
                f"Hi {username},\n\n"
                f"You have been enrolled in {course_title}.\n"
                f"Price: ₹{price}\n\n"
                "Thank you."
            )
            send_mail(
                subject,
                message,
                getattr(settings, "DEFAULT_FROM_EMAIL", ""),
                [email],
                fail_silently=True
            )
            email_sent = True
        except Exception:
            email_sent = False

    # Final response
    response = convert_objectids(saved)
    response["email_sent"] = email_sent

    return {
        "ok": True,
        "enrollment": response
    }
