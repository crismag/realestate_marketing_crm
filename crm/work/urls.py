from django.urls import path

from . import views

app_name = "work"
urlpatterns = [
    path("shared/", views.shared_work, name="shared"),
    path("claim/<int:contact_id>/", views.claim, name="claim"),
    path("handover/new/<int:contact_id>/", views.handover_new, name="handover_new"),
    path("handover/<int:pk>/<str:decision>/", views.handover_decide, name="handover_decide"),
    path("tasks/", views.tasks, name="tasks"),
    path("tasks/new/<int:contact_id>/", views.task_create, name="task_create"),
    path("tasks/<int:pk>/", views.task_detail, name="task"),
    path("tasks/<int:pk>/complete/", views.task_complete, name="task_complete"),
    path("tasks/<int:pk>/cancel/", views.task_cancel, name="task_cancel"),
]
