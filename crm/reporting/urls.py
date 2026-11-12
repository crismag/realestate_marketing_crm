from django.urls import path

from . import views

app_name = "reporting"
urlpatterns = [
    path("", views.index, name="index"),
    path("drill/", views.drill, name="drill"),
    path("spend/", views.spend, name="spend"),
]
