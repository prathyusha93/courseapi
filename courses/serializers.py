# courses/serializers.py
from rest_framework import serializers
from datetime import datetime


# ===========================================================
# AUTO TIMESTAMP
# ===========================================================
def now_timestamp(*args, **kwargs):
    return datetime.utcnow().isoformat()


# ===========================================================
# COMMON METADATA SERIALIZER
# ===========================================================
class SubCategorySerializer(serializers.Serializer):
    name = serializers.CharField()


class CategorySerializer(serializers.Serializer):
    name = serializers.CharField()
    sub_category = SubCategorySerializer(required=False)


class CommonMetadataSerializer(serializers.Serializer):
    category = CategorySerializer(required=False)
    tags = serializers.ListField(
        child=serializers.CharField(), required=False
    )
    created_by = serializers.CharField(required=False, allow_blank=True)
    updated_by = serializers.CharField(required=False, allow_blank=True)
    created_at = serializers.CharField(required=False, allow_blank=True)
    updated_at = serializers.CharField(required=False, allow_blank=True)


# ===========================================================
# CONTENT SERIALIZERS
# ===========================================================
class ContentIDFormatSerializer(serializers.Serializer):
    content_id = serializers.CharField()
    format = serializers.CharField()


class MediaContentIDsSerializer(serializers.Serializer):
    content_ids = serializers.ListField(
        child=ContentIDFormatSerializer()
    )
    metadata = CommonMetadataSerializer(required=False)


class ContentVersionSerializer(serializers.Serializer):
    versionid = serializers.CharField()
    type = serializers.CharField()
    title = serializers.CharField()
    data = serializers.CharField()
    url = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    metadata = CommonMetadataSerializer(required=False)


class ContentSerializer(serializers.Serializer):
    id = serializers.CharField(source="_id", required=False)

    versions = ContentVersionSerializer(many=True)
    topic_id = serializers.CharField(required=True)

    metadata = CommonMetadataSerializer(required=False)

    created_by = serializers.HiddenField(default="Prathyusha")
    updated_by = serializers.HiddenField(default="Prathyusha")
    created_at = serializers.HiddenField(default=now_timestamp)
    updated_at = serializers.HiddenField(default=now_timestamp)


# ===========================================================
# TOPIC SERIALIZER
# ===========================================================
class TopicSerializer(serializers.Serializer):
    id = serializers.CharField(source="_id", required=False)

    module_id = serializers.CharField(required=True)
    title = serializers.CharField(required=True)
    description = serializers.CharField(required=False, allow_blank=True)

    # matches your actual structure:
    # "media_content_ids": [{ "content_ids": [ {content_id, format}, ... ] }]
    media_content_ids = MediaContentIDsSerializer(many=True, required=False)

    # NEW FIELD YOU REQUESTED
    # "question_bank_configs": ["6746b8a650e9e527a828b4e8", ...]
    question_bank_configs = serializers.ListField(
        child=serializers.CharField(),
        required=False
    )

    metadata = serializers.DictField(required=False)

    created_by = serializers.HiddenField(default="Prathyusha")
    updated_by = serializers.HiddenField(default="Prathyusha")
    created_at = serializers.HiddenField(default=now_timestamp)
    updated_at = serializers.HiddenField(default=now_timestamp)
# ===========================================================
# MODULE SERIALIZER
# ===========================================================
class ModuleSerializer(serializers.Serializer):
    id = serializers.CharField(source="_id", required=False)

    course_id = serializers.CharField(required=True)
    title = serializers.CharField(required=True)
    description = serializers.CharField(required=False, allow_blank=True)

    # topic_ids = standard LMS structure
    topic_ids = serializers.ListField(
        child=serializers.CharField(), required=False
    )

    metadata = CommonMetadataSerializer(required=False)

    created_by = serializers.HiddenField(default="Prathyusha")
    updated_by = serializers.HiddenField(default="Prathyusha")
    created_at = serializers.HiddenField(default=now_timestamp)
    updated_at = serializers.HiddenField(default=now_timestamp)


# ===========================================================
# COURSE SERIALIZER
# ===========================================================
class CourseSerializer(serializers.Serializer):
    id = serializers.CharField(source="_id", required=False)

    course_title = serializers.CharField(max_length=512)
    course_description = serializers.CharField(required=False, allow_blank=True)

    segment = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    course_type = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    delivery_mode = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    is_locked = serializers.BooleanField(required=False)

    course_start_date = serializers.CharField(required=False, allow_blank=True)
    course_end_date = serializers.CharField(required=False, allow_blank=True)

    metadata = CommonMetadataSerializer(required=False)

    module_ids = serializers.ListField(
        child=serializers.CharField(), required=False
    )

    image_url = serializers.CharField(required=False, allow_blank=True)

    enrollers = serializers.IntegerField(required=False, default=0)
    progress = serializers.FloatField(required=False, default=0.0)

    difficulty_level = serializers.CharField(required=False, allow_blank=True)
    course_duration = serializers.CharField(required=False, allow_blank=True)

    display_price = serializers.DictField(required=False)

    created_by = serializers.HiddenField(default="Prathyusha")
    updated_by = serializers.HiddenField(default="Prathyusha")
    created_at = serializers.HiddenField(default=now_timestamp)
    updated_at = serializers.HiddenField(default=now_timestamp)


# ===========================================================
# ENROLLMENT SERIALIZER
# ===========================================================
class EnrollmentSerializer(serializers.Serializer):
    user_id = serializers.IntegerField(required=False)
    course_id = serializers.CharField(required=True)

    metadata = CommonMetadataSerializer(required=False)

    created_by = serializers.HiddenField(default="Prathyusha")
    updated_by = serializers.HiddenField(default="Prathyusha")
    created_at = serializers.HiddenField(default=now_timestamp)
    updated_at = serializers.HiddenField(default=now_timestamp)
