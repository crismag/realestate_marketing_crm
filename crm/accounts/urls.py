from django.urls import path

from . import views

app_name = "accounts"
urlpatterns = [
    path("login/", views.login_view, name="login"),
    path("login/verify/", views.login_verify, name="login_verify"),
    path("password-reset/", views.ResetRequestView.as_view(), name="password_reset"),
    path("password-reset/sent/", views.ResetSentView.as_view(), name="password_reset_sent"),
    path("password-reset/<uidb64>/<token>/", views.ResetConfirmView.as_view(), name="password_reset_confirm"),
    path("password-reset/done/", views.ResetCompleteView.as_view(), name="password_reset_complete"),
    path("two-step/", views.two_factor, name="two_factor"),
    path("logout/", views.logout_view, name="logout"),
    path("password/", views.password_change, name="password_change"),
    path("users/", views.users_list, name="users"),
    path("users/new/", views.user_create, name="user_create"),
    path("users/<int:pk>/", views.user_edit, name="user_edit"),
    path("users/<int:pk>/reset-password/", views.user_reset_password, name="user_reset_password"),
    path("users/<int:pk>/reset-two-step/", views.user_reset_two_factor, name="user_reset_two_factor"),
]
