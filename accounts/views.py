# accounts/views.py
from django.shortcuts import render, redirect
from django.contrib import messages
from django.core.signing import TimestampSigner, BadSignature, SignatureExpired
from django.utils.crypto import get_random_string
from django.contrib.auth import get_user_model
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny

from .forms import (
    ForgotPasswordForm,
    VerifyOTPForm,
    SendResetLinkForm,
    ResetPasswordForm,
)

from notifications.services import NotificationService

User = get_user_model()
signer = TimestampSigner()


# (optional) API endpoints left intact if you need JSON APIs later
class ForgotPasswordView(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        form = ForgotPasswordForm(request.data)
        if not form.is_valid():
            return Response({"errors": form.errors}, status=400)
        form.send_otp()
        return Response({"message": "OTP sent"}, status=200)


# FORM views (browser):
def forgot_password_form(request):
    if request.method == "POST":
        form = ForgotPasswordForm(request.POST)
        if form.is_valid():
            try:
                form.send_otp()
            except Exception as e:
                messages.error(request, str(e))
                return redirect("forgot_password")
            messages.success(request, "OTP sent to your email!")
            return redirect("verify_otp")
    else:
        form = ForgotPasswordForm()
    return render(request, "accounts/forgot_password.html", {"form": form})


def verify_otp_form(request):
    if request.method == "POST":
        form = VerifyOTPForm(request.POST)
        if form.is_valid():
            messages.success(request, "OTP verified!")
            return redirect("send_reset_link")
        else:
            # form errors appear on page
            pass
    else:
        form = VerifyOTPForm()
    return render(request, "accounts/verify_otp.html", {"form": form})


def send_reset_link_form(request):
    if request.method == "POST":
        form = SendResetLinkForm(request.POST)
        if form.is_valid():
            try:
                reset_link = form.send_reset_link()
            except Exception as e:
                messages.error(request, str(e))
                return redirect("send_reset_link")
            messages.success(request, "Password reset link sent to email!")
            # show a success page or redirect to root — we will show a small page
            return render(request, "accounts/reset_link_sent.html", {"reset_link": reset_link})
    else:
        form = SendResetLinkForm()
    return render(request, "accounts/send_reset_link.html", {"form": form})


def reset_password_form(request):
    token = request.GET.get("token", "") or request.POST.get("token", "")
    if request.method == "POST":
        form = ResetPasswordForm(request.POST)
        if form.is_valid():
            try:
                form.save_password()
            except Exception as e:
                messages.error(request, str(e))
                return redirect("forgot_password")
            # go to a simple success page (avoids relying on a named 'login' view)
            return render(request, "accounts/reset_success.html")
    else:
        form = ResetPasswordForm(initial={"token": token})
    return render(request, "accounts/reset_password.html", {"form": form})
