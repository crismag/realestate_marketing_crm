from django.urls import include, path

urlpatterns = [
    path("", include("crm.core.urls")),
    path("accounts/", include("crm.accounts.urls")),
    path("contacts/", include("crm.contacts.urls")),
    path("work/", include("crm.work.urls")),
    path("attention/", include("crm.attention.urls")),
    path("automation/", include("crm.automation.urls")),
    path("messages/", include("crm.comms.urls")),
    path("reports/", include("crm.reporting.urls")),
]

handler404 = "crm.core.views.not_found"
handler500 = "crm.core.views.server_error"
handler403 = "crm.core.views.permission_denied"
