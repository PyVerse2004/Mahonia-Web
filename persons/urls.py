from django.urls import path

from .views import (
    PersonCreateView,
    PersonDeleteView,
    PersonListView,
    PersonSettleView,
    PersonUpdateView,
)

app_name = "persons"

urlpatterns = [
    path("", PersonListView.as_view(), name="person_list"),
    path("create/", PersonCreateView.as_view(), name="person_create"),
    path("<int:pk>/edit/", PersonUpdateView.as_view(), name="person_update"),
    path("<int:pk>/delete/", PersonDeleteView.as_view(), name="person_delete"),
    path("<int:pk>/settle/", PersonSettleView.as_view(), name="person_settle"),
]
