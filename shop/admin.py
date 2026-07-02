from django.contrib import admin

from shop.models import ProcessedMessage, Product, CommentKeywordRule, VideoPost


@admin.register(VideoPost)
class VideoPostAdmin(admin.ModelAdmin):
    list_display = ("title", "media_id", "is_active", "updated_at")
    list_filter = ("is_active",)
    search_fields = ("title", "media_id", "caption")


@admin.register(CommentKeywordRule)
class CommentKeywordRuleAdmin(admin.ModelAdmin):
    list_display = ("keyword", "video", "match_type", "is_active", "priority", "send_dm")
    list_filter = ("is_active", "match_type", "send_dm")
    search_fields = ("keyword", "public_reply")


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("product_name", "category", "price", "balance", "source", "barcode", "updated_at")
    list_filter = ("source", "category")
    search_fields = ("product_name", "barcode", "external_id", "category", "keywords")
    ordering = ("product_name",)


@admin.register(ProcessedMessage)
class ProcessedMessageAdmin(admin.ModelAdmin):
    list_display = ("message_key", "message_type", "processed_at")
    list_filter = ("message_type",)
    search_fields = ("message_key",)
