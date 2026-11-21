from jalali_date.widgets import AdminJalaliDateWidget


class JalaliDateInput(AdminJalaliDateWidget):
    """
    Custom Jalali date widget omitting Django admin's wrapper <p class="date">
    for pixel-perfect alignment in Bootstrap form controls and filter bars.
    """

    template_name = "django/forms/widgets/input.html"
