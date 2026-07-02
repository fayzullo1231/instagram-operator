from django.db import models


class Product(models.Model):
    SOURCE_LINKO = "linko"
    SOURCE_MDOKON = "mdokon"
    SOURCE_TEZPOS = "tezpos"

    external_id = models.CharField(max_length=255)
    product_name = models.CharField(max_length=500, db_index=True)
    category = models.CharField(max_length=200, blank=True, default="", db_index=True)
    keywords = models.CharField(max_length=500, blank=True, default="")
    barcode = models.CharField(max_length=100, blank=True, null=True)
    price = models.FloatField(default=0)
    balance = models.FloatField(default=0)
    source = models.CharField(max_length=50, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "products"
        unique_together = ("source", "external_id")
        ordering = ["product_name"]
        verbose_name = "Mahsulot"
        verbose_name_plural = "Mahsulotlar"

    def __str__(self) -> str:
        return self.product_name


class ProcessedMessage(models.Model):
    TYPE_DM = "dm"
    TYPE_COMMENT = "comment"

    message_key = models.CharField(max_length=255, unique=True)
    message_type = models.CharField(max_length=20)
    processed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "processed_messages"
        verbose_name = "Qayta ishlangan xabar"
        verbose_name_plural = "Qayta ishlangan xabarlar"

    def __str__(self) -> str:
        return self.message_key


class VideoPost(models.Model):
    """Instagram post/reel — izoh kalit so'z qoidalari uchun."""

    media_id = models.CharField(max_length=255, unique=True, db_index=True)
    title = models.CharField(max_length=500, blank=True, default="")
    caption = models.TextField(blank=True, default="")
    permalink = models.URLField(blank=True, default="")
    thumbnail_url = models.URLField(blank=True, default="")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "video_posts"
        ordering = ["-updated_at"]
        verbose_name = "Instagram post"
        verbose_name_plural = "Instagram postlar"

    def __str__(self) -> str:
        return self.title or self.media_id[:20]

    @property
    def rules_count(self) -> int:
        return self.keyword_rules.filter(is_active=True).count()


class CommentKeywordRule(models.Model):
    MATCH_CONTAINS = "contains"
    MATCH_EXACT = "exact"
    MATCH_STARTS = "starts_with"
    MATCH_CHOICES = [
        (MATCH_CONTAINS, "O'z ichiga oladi"),
        (MATCH_EXACT, "To'liq mos"),
        (MATCH_STARTS, "Boshlanadi"),
    ]

    video = models.ForeignKey(
        VideoPost,
        on_delete=models.CASCADE,
        related_name="keyword_rules",
        null=True,
        blank=True,
        help_text="Qaysi video/post uchun — tanlanmasa barcha postlarga qo'llanadi",
    )
    keyword = models.CharField(max_length=200, db_index=True)
    match_type = models.CharField(max_length=20, choices=MATCH_CHOICES, default=MATCH_CONTAINS)
    public_reply = models.TextField(
        blank=True,
        default="",
        help_text="Izoh ostidagi matn javob (ixtiyoriy, rasm bo'lsa ham yozish mumkin)",
    )
    reply_image = models.ImageField(
        upload_to="rule_images/",
        blank=True,
        null=True,
        help_text="Javob rasmi — Direct xabar orqali yuboriladi",
    )
    dm_reply = models.TextField(blank=True, default="", help_text="Direct matn xabar (ixtiyoriy)")
    dm_image = models.ImageField(
        upload_to="rule_images/dm/",
        blank=True,
        null=True,
        help_text="Alohida DM rasmi (bo'sh bo'lsa reply_image ishlatiladi)",
    )
    send_dm = models.BooleanField(
        default=True,
        help_text="Rasm yoki DM matn yuborish (izohdan keyin Direct)",
    )
    is_active = models.BooleanField(default=True)
    priority = models.IntegerField(default=0, help_text="Katta raqam — birinchi tekshiriladi")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "comment_keyword_rules"
        ordering = ["-priority", "keyword"]
        verbose_name = "Izoh kalit so'z qoidasi"
        verbose_name_plural = "Izoh kalit so'z qoidalari"

    def __str__(self) -> str:
        scope = self.video.title if self.video_id and self.video else "Barcha postlar"
        return f"{self.keyword} → {scope}"

    @property
    def has_image_reply(self) -> bool:
        return bool(self.reply_image or self.dm_image)
