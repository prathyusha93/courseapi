from django.urls import path
from . import views

urlpatterns = [
    path("forgot-password/", views.forgot_password_form, name="forgot_password"),
    path("verify-otp/", views.verify_otp_form, name="verify_otp"),
    path("send-reset-link/", views.send_reset_link_form, name="send_reset_link"),
    path("reset-password/", views.reset_password_form, name="reset_password"),
]
