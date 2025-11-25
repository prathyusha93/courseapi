# accounts/forms.py
from django import forms
from django.core.signing import TimestampSigner, BadSignature, SignatureExpired
from django.utils.crypto import get_random_string
from django.contrib.auth import get_user_model
from notifications.services import NotificationService

User = get_user_model()
signer = TimestampSigner()

class ForgotPasswordForm(forms.Form):
    email = forms.EmailField()

    def send_otp(self):
        email = self.cleaned_data["email"]
        user = User.objects.filter(email__iexact=email).first()
        if not user:
            raise forms.ValidationError("Email not found")

        otp = get_random_string(6, "0123456789")
        user.profile_otp = otp
        user.save()

        NotificationService.send(
            event_name="USER_FORGOT_PASSWORD",
            ctx={"username": user.username, "otp": otp},
            to_email=user.email,
        )
        return True


class VerifyOTPForm(forms.Form):
    email = forms.EmailField()
    otp = forms.CharField(max_length=10)

    def clean(self):
        cleaned = super().clean()
        email = cleaned.get("email")
        otp = cleaned.get("otp")
        user = User.objects.filter(email__iexact=email).first()
        if not user:
            raise forms.ValidationError("User not found")
        if user.profile_otp != otp:
            raise forms.ValidationError("Invalid OTP")
        return cleaned


class SendResetLinkForm(forms.Form):
    email = forms.EmailField()

    def send_reset_link(self):
        email = self.cleaned_data["email"]
        user = User.objects.filter(email__iexact=email).first()
        if not user:
            raise forms.ValidationError("User not found")

        token = signer.sign(user.email)
        reset_link = f"http://127.0.0.1:8000/api/auth/reset-password/?token={token}"

        NotificationService.send(
            event_name="USER_PASSWORD_RESET",
            ctx={"username": user.username, "reset_link": reset_link},
            to_email=user.email,
        )
        return reset_link


class ResetPasswordForm(forms.Form):
    token = forms.CharField(widget=forms.HiddenInput())
    new_password = forms.CharField(widget=forms.PasswordInput(), min_length=4)
    confirm_password = forms.CharField(widget=forms.PasswordInput(), min_length=4)

    def clean(self):
        cleaned = super().clean()
        np = cleaned.get("new_password")
        cp = cleaned.get("confirm_password")
        if np != cp:
            raise forms.ValidationError("Passwords do not match")
        # validate token
        token = cleaned.get("token")
        try:
            signer.unsign(token, max_age=3600)
        except SignatureExpired:
            raise forms.ValidationError("Reset link expired")
        except BadSignature:
            raise forms.ValidationError("Invalid reset link")
        return cleaned

    def save_password(self):
        token = self.cleaned_data["token"]
        email = signer.unsign(token)
        user = User.objects.filter(email__iexact=email).first()
        if not user:
            raise forms.ValidationError("User not found")
        user.set_password(self.cleaned_data["new_password"])
        user.profile_otp = ""  # clear OTP
        user.save()
        return True
