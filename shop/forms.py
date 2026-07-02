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
    class Meta:
        model = CommentKeywordRule
        fields = (
            "video",
            "keyword",
            "match_type",
            "public_reply",
            "dm_reply",
            "send_dm",
            "is_active",
            "priority",
        )
        widgets = {
            "video": forms.Select(attrs={"class": "form-select"}),
            "keyword": forms.TextInput(attrs={"class": "form-input", "placeholder": "narx, qancha, bormi..."}),
            "match_type": forms.Select(attrs={"class": "form-select"}),
            "public_reply": forms.Textarea(
                attrs={"class": "form-textarea", "rows": 4, "placeholder": "Izoh ostidagi javob"}
            ),
            "dm_reply": forms.Textarea(
                attrs={"class": "form-textarea", "rows": 4, "placeholder": "Direct xabar (ixtiyoriy)"}
            ),
            "send_dm": forms.CheckboxInput(attrs={"class": "form-checkbox"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-checkbox"}),
            "priority": forms.NumberInput(attrs={"class": "form-input", "style": "max-width:120px"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["video"].queryset = VideoPost.objects.filter(is_active=True).order_by("-updated_at")
        self.fields["video"].required = False
        self.fields["video"].empty_label = "— Barcha postlar —"
