from django.urls import path

from . import views

app_name = "comms"
urlpatterns = [
    path("", views.message_list, name="list"),
    path("<int:pk>/", views.message_detail, name="detail"),
    path("<int:pk>/retry/", views.message_retry, name="retry"),
    path("<int:pk>/resolve/", views.message_resolve, name="resolve"),
    path("templates/<int:pk>/", views.template_edit, name="template"),
]
