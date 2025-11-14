from rest_framework import serializers


class ObjectIdStrField(serializers.CharField):
    """Validate MongoDB ObjectId (24 char hex)."""
    def __init__(self, **kwargs):
        kwargs.setdefault("min_length", 24)
        kwargs.setdefault("max_length", 24)
        super().__init__(**kwargs)


# ---------------- CATEGORY -----------------
class CategorySerializer(serializers.Serializer):
    name = serializers.CharField()
    sub_category = serializers.DictField(required=False)


# ---------------- CONTENT ------------------
class ContentVersionMetadataSerializer(serializers.Serializer):
    duration = serializers.IntegerField(required=False)
    format = serializers.CharField(required=False)
    category = CategorySerializer(required=False)
    tags = serializers.ListField(child=serializers.CharField(), required=False)


class ContentVersionSerializer(serializers.Serializer):
    versionid = serializers.CharField()
    type = serializers.CharField()
    title = serializers.CharField()
    data = serializers.CharField(required=False, allow_null=True)
    url = serializers.CharField(required=False, allow_null=True)
    metadata = ContentVersionMetadataSerializer(required=False)


class ContentSerializer(serializers.Serializer):
    _id = ObjectIdStrField(required=False)
    versions = serializers.ListField(child=ContentVersionSerializer())


# ---------------- TOPIC -------------------
class TopicContentIdSerializer(serializers.Serializer):
    content_id = ObjectIdStrField()
    format = serializers.CharField()


class TopicMediaGroupSerializer(serializers.Serializer):
    content_ids = serializers.ListField(child=TopicContentIdSerializer())


class TopicSerializer(serializers.Serializer):
    _id = ObjectIdStrField(required=False)
    title = serializers.CharField()
    media_content_ids = serializers.ListField(child=TopicMediaGroupSerializer(), required=False)


# ---------------- MODULE -------------------
class ModuleSerializer(serializers.Serializer):
    _id = ObjectIdStrField(required=False)
    title = serializers.CharField()
    description = serializers.CharField(required=False)
    metadata = serializers.DictField(required=False)
    category = CategorySerializer(required=False)
    sub_category = CategorySerializer(required=False)
    tags = serializers.ListField(child=serializers.CharField(), required=False)
    topic_ids = serializers.ListField(child=ObjectIdStrField(), required=False)


# ---------------- COURSE -------------------
class MoneySerializer(serializers.Serializer):
    amount = serializers.IntegerField()
    currency = serializers.CharField()


class CourseSerializer(serializers.Serializer):
    _id = ObjectIdStrField(required=False)
    course_title = serializers.CharField()
    course_description = serializers.CharField()
    course_start_date = serializers.DateTimeField()
    course_end_date = serializers.DateTimeField()

    metadata = serializers.DictField(required=False)
    category = CategorySerializer(required=False)
    sub_category = CategorySerializer(required=False)
    tags = serializers.ListField(child=serializers.CharField(), required=False)

    mode = serializers.CharField(required=False)
    module_ids = serializers.ListField(child=ObjectIdStrField(), required=False)
    segment = serializers.CharField(required=False)
    course_type = serializers.CharField(required=False)
    delivery_mode = serializers.CharField(required=False)
    is_locked = serializers.BooleanField(required=False)
    image_url = serializers.CharField(required=False)
    progress = serializers.IntegerField(required=False)
    difficulty_level = serializers.CharField(required=False)
    display_price = MoneySerializer(required=False)

    created_by = serializers.CharField(required=False)
    updated_by = serializers.CharField(required=False)
    created_at = serializers.CharField(required=False)
    updated_at = serializers.CharField(required=False)


# ---------------- ENROLLMENTS -------------------
from rest_framework import serializers

class EnrollmentSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)

    course_id = serializers.CharField()
    enrolled_at = serializers.DateTimeField(required=False)
    progress = serializers.IntegerField(default=0)
