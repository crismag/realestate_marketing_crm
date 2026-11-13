from django.urls import path

from . import views

app_name = "contacts"
urlpatterns = [
    path("", views.contact_list, name="list"),
    path("new/", views.contact_new, name="new"),
    path("import/", views.import_start, name="import"),
    path("import/template.csv", views.import_template, name="import_template"),
    path("import/<int:pk>/", views.import_detail, name="import_detail"),
    path("opportunities/", views.opportunities, name="opportunities"),
    path("opportunities/<int:opp_id>/stage/", views.opportunity_stage, name="opportunity_stage"),
    path("<int:pk>/", views.contact_detail, name="detail"),
    path("<int:pk>/edit/", views.contact_edit, name="edit"),
    path("<int:pk>/merge/<int:duplicate_pk>/", views.contact_merge, name="merge"),
    path("<int:pk>/lifecycle/", views.contact_lifecycle, name="lifecycle"),
    path("<int:pk>/opt-out/", views.contact_opt_out, name="opt_out"),
    path("<int:pk>/archive/", views.contact_archive, name="archive"),
    path("<int:pk>/inquiries/", views.add_inquiry, name="add_inquiry"),
    path("<int:pk>/inquiries/<int:inquiry_id>/close/", views.close_inquiry, name="close_inquiry"),
    path("<int:pk>/interactions/", views.add_interaction, name="add_interaction"),
    path("<int:pk>/watch/", views.toggle_watch, name="watch"),
    path("<int:pk>/opportunities/", views.add_opportunity, name="add_opportunity"),
    path("<int:pk>/opportunities/<int:opp_id>/", views.opportunity_edit, name="opportunity"),
    path("<int:pk>/opportunities/<int:opp_id>/outcome/", views.opportunity_outcome, name="opportunity_outcome"),
]
