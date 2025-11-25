from django.db import models

class NotificationTemplate(models.Model):
    EVENT_CHOICES = [
    ("USER_REGISTERED", "User Registered"),
    ("USER_FORGOT_PASSWORD", "Forgot Password OTP"),
    ("USER_PASSWORD_RESET", "Reset Password Link"),
    ("COURSE_ENROLLED", "Course Enrolled"),
    ("COURSE_50_PERCENT", "Course 50% Completed"),
    ("COURSE_COMPLETED", "Course Completed"),
]


    event_name = models.CharField(max_length=50, choices=EVENT_CHOICES, unique=True)
    subject = models.CharField(max_length=255)
    body = models.TextField()   # contains placeholders like {{username}} {{course}}
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.event_name
