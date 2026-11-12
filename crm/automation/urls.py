from django.urls import path

from . import views

app_name = "automation"
urlpatterns = [
    path("rules/", views.index, name="index"),
    path("rules/<slug:key>/", views.rule_detail, name="rule"),
    path("jobs/", views.jobs, name="jobs"),
    path("jobs/<int:pk>/", views.job_detail, name="job"),
    path("jobs/<int:pk>/<str:action>/", views.job_action, name="job_action"),
    path("notifications/", views.notifications, name="notifications"),
    path("notifications/read-all/", views.notifications_read_all, name="notifications_read_all"),
    path("notifications/<int:pk>/<str:action>/", views.notification_action, name="notification_action"),
]
