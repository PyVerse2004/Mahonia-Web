from django.urls import path

from .views import ProfitLossReportView

app_name = "profit_loss"

urlpatterns = [
    path("", ProfitLossReportView.as_view(), name="report"),
]
