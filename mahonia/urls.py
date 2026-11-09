from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView

urlpatterns = [
    path("", RedirectView.as_view(pattern_name="dashboard", permanent=False)),
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls")),
    path("inventory/", include("inventory.urls")),
    path("purchases/", include("purchases.urls")),
    path("sales/", include("daily_sales.urls")),
    path("persons/", include("persons.urls")),
    path("profit-loss/", include("profit_loss.urls")),
]
