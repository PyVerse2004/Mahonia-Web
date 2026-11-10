from django import forms
from django.contrib.auth.forms import AuthenticationForm

from .models import UserProfile


class LoginForm(AuthenticationForm):
    role = forms.ChoiceField(
        label="نقش",
        choices=[
            (UserProfile.ROLE_SELLER, "فروشنده"),
            (UserProfile.ROLE_MANAGER, "مدیر"),
        ],
        initial=UserProfile.ROLE_SELLER,
        widget=forms.Select(attrs={"class": "form-select"}),
        required=False,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].label = "نام کاربری"
        self.fields["password"].label = "رمز عبور"
        self.fields["role"].label = "نقش"
        self.fields["username"].widget.attrs.update(
            {"class": "form-control", "autofocus": True}
        )
        self.fields["password"].widget.attrs.update({"class": "form-control"})
        self.fields["role"].widget.attrs.update({"class": "form-select"})

    def clean(self):
        cleaned_data = super().clean()
        if self.user_cache is not None:
            selected_role = cleaned_data.get("role")
            user = self.user_cache

            default_role = (
                UserProfile.ROLE_MANAGER if user.is_superuser else UserProfile.ROLE_SELLER
            )
            profile, _ = UserProfile.objects.get_or_create(
                user=user, defaults={"role": default_role}
            )

            # اگر نقش در فرم ارسال نشده بود (مانند تست‌های قدیمی)، از نقش اختصاص یافته به کاربر استفاده شود
            if not selected_role:
                selected_role = profile.role
                cleaned_data["role"] = selected_role

            # مدیر کل دسترسی با هر دو نقش را دارد
            if user.is_superuser:
                return cleaned_data

            # اگر کاربر فروشنده است اما در فرم نقش مدیر را انتخاب کرده باشد:
            if (
                selected_role == UserProfile.ROLE_MANAGER
                and profile.role != UserProfile.ROLE_MANAGER
            ):
                raise forms.ValidationError("شما دسترسی ورود با نقش مدیر را ندارید.")

        return cleaned_data
