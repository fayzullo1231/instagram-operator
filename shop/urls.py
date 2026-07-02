from django.urls import path

from shop import views

urlpatterns = [
    path("health", views.health, name="health"),
    path("ready", views.ready, name="ready"),
    path("api/v1/chat", views.chat, name="chat"),
    path("api/v1/sync", views.sync_products, name="sync"),
    path("api/v1/sync/status", views.sync_status, name="sync_status"),
    path("api/v1/instagram/status", views.instagram_status, name="instagram_status"),
    path("api/v1/instagram/poll", views.instagram_poll, name="instagram_poll"),
]
