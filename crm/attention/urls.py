from django.urls import path

from . import views

app_name = "attention"
urlpatterns = [
    path("", views.queue, name="queue"),
    path("snooze/<int:contact_id>/", views.snooze, name="snooze"),
    path("unsnooze/<int:contact_id>/", views.unsnooze, name="unsnooze"),
]
