from django.urls import path

from shop import panel_views

urlpatterns = [
    path("login/", panel_views.panel_login, name="panel_login"),
    path("logout/", panel_views.panel_logout, name="panel_logout"),
    path("", panel_views.panel_dashboard, name="panel_dashboard"),
    path("sync/products/", panel_views.product_sync_now, name="panel_product_sync"),
    path("videos/", panel_views.video_list, name="panel_video_list"),
    path("videos/create/", panel_views.video_create, name="panel_video_create"),
    path("videos/<int:pk>/edit/", panel_views.video_edit, name="panel_video_edit"),
    path("videos/<int:pk>/delete/", panel_views.video_delete, name="panel_video_delete"),
    path("videos/sync/", panel_views.video_sync_instagram, name="panel_video_sync"),
    path("rules/", panel_views.rule_list, name="panel_rule_list"),
    path("rules/create/", panel_views.rule_create, name="panel_rule_create"),
    path("rules/<int:pk>/edit/", panel_views.rule_edit, name="panel_rule_edit"),
    path("rules/<int:pk>/delete/", panel_views.rule_delete, name="panel_rule_delete"),
    path("rules/<int:pk>/toggle/", panel_views.rule_toggle, name="panel_rule_toggle"),
    path("products/", panel_views.product_list, name="panel_product_list"),
]
