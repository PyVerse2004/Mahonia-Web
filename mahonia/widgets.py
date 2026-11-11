from jalali_date.widgets import AdminJalaliDateWidget


class JalaliDateInput(AdminJalaliDateWidget):
    """
    ویجت تاریخ جلالی اختصاصی بدون تگ پوشاننده <p class="date"> جنگو ادمین
    جهت هم‌ترازسازی دقیق پیکسلی در سطرهای فیلتر و گروه‌های ورودی بوت‌استرپ.
    """
    template_name = "django/forms/widgets/input.html"

