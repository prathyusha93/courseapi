# courses/serializers.py
from rest_framework import serializers

class ContentSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255)
    body = serializers.CharField(allow_blank=True, required=False)


class TopicSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255)
    description = serializers.CharField(allow_blank=True, required=False)


class ModuleSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255)
    description = serializers.CharField(allow_blank=True, required=False)
    topic_ids = serializers.ListField(child=serializers.CharField(), required=False)


class CourseSerializer(serializers.Serializer):
    course_title = serializers.CharField(max_length=512)
    course_description = serializers.CharField(allow_blank=True, required=False)
    segment = serializers.CharField(max_length=100, required=False, allow_null=True)
    course_type = serializers.CharField(required=False, allow_null=True)
    delivery_mode = serializers.CharField(required=False, allow_null=True)
    is_locked = serializers.BooleanField(required=False, default=False)
    course_start_date = serializers.CharField(required=False, allow_blank=True)
    course_end_date = serializers.CharField(required=False, allow_blank=True)
    metadata = serializers.DictField(child=serializers.JSONField(), required=False)
    module_ids = serializers.ListField(child=serializers.CharField(), required=False)
    image_url = serializers.CharField(required=False, allow_blank=True)
    enrollers = serializers.IntegerField(required=False, default=0)
    progress = serializers.IntegerField(required=False, default=0)
    difficulty_level = serializers.CharField(required=False, allow_blank=True)
    course_duration = serializers.CharField(required=False, allow_blank=True)
    display_price = serializers.DictField(required=False, child=serializers.IntegerField(), allow_empty=True)


class EnrollmentSerializer(serializers.Serializer):
    # Used by EnrollmentViewSet.create (self-enroll or admin endpoint)
    user_id = serializers.IntegerField(required=False)
    course_id = serializers.CharField()
