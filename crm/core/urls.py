from django.urls import path

from . import views

app_name = "core"
urlpatterns = [
    path("", views.today, name="today"),
    path("healthz", views.healthz, name="healthz"),
    path("settings/", views.settings_index, name="settings"),
    path("settings/audit/", views.audit_log, name="audit"),
    path("settings/pools/new/", views.pool_edit, name="pool_new"),
    path("settings/pools/<int:pk>/", views.pool_edit, name="pool_edit"),
    path("settings/teams/new/", views.team_edit, name="team_new"),
    path("settings/teams/<int:pk>/", views.team_edit, name="team_edit"),
    path("settings/sources/new/", views.source_edit, name="source_new"),
    path("settings/sources/<int:pk>/", views.source_edit, name="source_edit"),
]
