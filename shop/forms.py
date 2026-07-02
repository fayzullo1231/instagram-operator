from django import forms

from shop.models import CommentKeywordRule, VideoPost


class VideoPostForm(forms.ModelForm):
    class Meta:
        model = VideoPost
        fields = ("media_id", "title", "caption", "permalink", "thumbnail_url", "is_active")
        widgets = {
            "media_id": forms.TextInput(attrs={"class": "form-input", "placeholder": "Instagram media ID"}),
            "title": forms.TextInput(attrs={"class": "form-input", "placeholder": "Masalan: Zateya moy reklama"}),
            "caption": forms.Textarea(attrs={"class": "form-textarea", "rows": 3}),
            "permalink": forms.URLInput(attrs={"class": "form-input", "placeholder": "https://instagram.com/p/..."}),
            "thumbnail_url": forms.URLInput(attrs={"class": "form-input"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-checkbox"}),
        }


class CommentKeywordRuleForm(forms.ModelForm):
    apply_to_all_videos = forms.BooleanField(
        required=False,
        initial=False,
        label="Barcha videolarga qo'llash",
        widget=forms.CheckboxInput(attrs={"class": "form-checkbox", "id": "apply-all-videos"}),
    )

    class Meta:
        model = CommentKeywordRule
        fields = (
            "video",
            "keyword",
            "match_type",
            "public_reply",
            "reply_image",
            "dm_reply",
            "dm_image",
            "send_dm",
            "is_active",
            "priority",
        )
        widgets = {
            "video": forms.RadioSelect(attrs={"class": "video-radio-list"}),
            "keyword": forms.TextInput(attrs={"class": "form-input", "placeholder": "narx, qancha, bormi..."}),
            "match_type": forms.Select(attrs={"class": "form-select"}),
            "public_reply": forms.Textarea(
                attrs={"class": "form-textarea", "rows": 3, "placeholder": "Izoh ostidagi javob (ixtiyoriy)"}
            ),
            "reply_image": forms.ClearableFileInput(attrs={"class": "form-input", "accept": "image/*"}),
            "dm_reply": forms.Textarea(
                attrs={"class": "form-textarea", "rows": 3, "placeholder": "Direct matn xabar (ixtiyoriy)"}
            ),
            "dm_image": forms.ClearableFileInput(attrs={"class": "form-input", "accept": "image/*"}),
            "send_dm": forms.CheckboxInput(attrs={"class": "form-checkbox"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-checkbox"}),
            "priority": forms.NumberInput(attrs={"class": "form-input", "style": "max-width:120px"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["video"].queryset = VideoPost.objects.filter(is_active=True).order_by("-updated_at")
        self.fields["video"].required = False
        self.fields["video"].empty_label = None
        if self.instance and self.instance.pk and not self.instance.video_id:
            self.fields["apply_to_all_videos"].initial = True

    def clean(self):
        cleaned = super().clean()
        apply_all = cleaned.get("apply_to_all_videos")
        video = cleaned.get("video")
        public_reply = (cleaned.get("public_reply") or "").strip()
        reply_image = cleaned.get("reply_image")
        dm_reply = (cleaned.get("dm_reply") or "").strip()
        dm_image = cleaned.get("dm_image")

        if apply_all:
            cleaned["video"] = None
        elif not video:
            raise forms.ValidationError("Videoni tanlang yoki 'Barcha videolarga qo'llash' ni belgilang.")

        has_existing_image = self.instance.pk and (
            self.instance.reply_image or self.instance.dm_image
        )
        has_image = bool(reply_image or dm_image or has_existing_image)
        if not public_reply and not has_image and not dm_reply:
            raise forms.ValidationError(
                "Kamida bitta javob kerak: izoh matni, rasm yoki Direct matn."
            )
        return cleaned
