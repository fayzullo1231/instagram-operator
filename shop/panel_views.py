import logging

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from shop.forms import CommentKeywordRuleForm, VideoPostForm
from shop.models import CommentKeywordRule, Product, ProcessedMessage, VideoPost
from shop.services.instagram_service import InstagramService
from shop.services.product_sync import ProductSyncService

logger = logging.getLogger(__name__)


def panel_login(request: HttpRequest) -> HttpResponse:
    if request.user.is_authenticated:
        return redirect("panel_dashboard")

    error = ""
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            return redirect(request.GET.get("next") or "panel_dashboard")
        error = "Login yoki parol noto'g'ri"

    return render(request, "panel/login.html", {"error": error})


@login_required(login_url="panel_login")
def panel_logout(request: HttpRequest) -> HttpResponse:
    logout(request)
    return redirect("panel_login")


@login_required(login_url="panel_login")
def panel_dashboard(request: HttpRequest) -> HttpResponse:
    instagram = InstagramService().get_status()
    sync = ProductSyncService().get_sync_status()
    context = {
        "stats": {
            "products": sync["total_count"],
            "videos": VideoPost.objects.count(),
            "rules": CommentKeywordRule.objects.filter(is_active=True).count(),
            "processed": ProcessedMessage.objects.count(),
        },
        "instagram": instagram,
        "sync": sync,
        "recent_rules": CommentKeywordRule.objects.select_related("video").order_by("-updated_at")[:8],
        "recent_videos": VideoPost.objects.annotate(
            rule_count=Count("keyword_rules")
        ).order_by("-updated_at")[:6],
    }
    return render(request, "panel/dashboard.html", context)


@login_required(login_url="panel_login")
def video_list(request: HttpRequest) -> HttpResponse:
    videos = VideoPost.objects.annotate(rule_count=Count("keyword_rules")).order_by("-updated_at")
    return render(request, "panel/videos/list.html", {"videos": videos})


@login_required(login_url="panel_login")
@require_http_methods(["GET", "POST"])
def video_create(request: HttpRequest) -> HttpResponse:
    form = VideoPostForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Post qo'shildi")
        return redirect("panel_video_list")
    return render(request, "panel/videos/form.html", {"form": form, "title": "Yangi post"})


@login_required(login_url="panel_login")
@require_http_methods(["GET", "POST"])
def video_edit(request: HttpRequest, pk: int) -> HttpResponse:
    video = get_object_or_404(VideoPost, pk=pk)
    form = VideoPostForm(request.POST or None, instance=video)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Post yangilandi")
        return redirect("panel_video_list")
    return render(
        request,
        "panel/videos/form.html",
        {"form": form, "title": "Postni tahrirlash", "video": video},
    )


@login_required(login_url="panel_login")
@require_POST
def video_delete(request: HttpRequest, pk: int) -> HttpResponse:
    video = get_object_or_404(VideoPost, pk=pk)
    video.delete()
    messages.success(request, "Post o'chirildi")
    return redirect("panel_video_list")


@login_required(login_url="panel_login")
@require_POST
def video_sync_instagram(request: HttpRequest) -> HttpResponse:
    service = InstagramService()
    if not service.get_status().get("connected"):
        messages.error(request, "Instagram ulanmagan — avval Zernio ni ulang")
        return redirect("panel_video_list")

    try:
        service.client.ensure_login()
        posts = service.client.zernio.list_posts_with_comments(limit=20)
        created = 0
        for post in posts:
            media_id = str(post.get("id", ""))
            if not media_id:
                continue
            caption = str(post.get("caption") or post.get("text") or "").strip()
            title = caption[:120] if caption else f"Post {media_id[:12]}"
            _, was_created = VideoPost.objects.update_or_create(
                media_id=media_id,
                defaults={
                    "title": title,
                    "caption": caption,
                    "permalink": str(post.get("permalink") or post.get("url") or ""),
                    "thumbnail_url": str(
                        post.get("thumbnailUrl") or post.get("mediaUrl") or post.get("imageUrl") or ""
                    ),
                    "is_active": True,
                },
            )
            if was_created:
                created += 1
        messages.success(request, f"Instagram dan {len(posts)} ta post yuklandi ({created} ta yangi)")
    except Exception as exc:
        logger.exception("Post sinxronizatsiya xatosi: %s", exc)
        messages.error(request, f"Xato: {exc}")

    return redirect("panel_video_list")


@login_required(login_url="panel_login")
def rule_list(request: HttpRequest) -> HttpResponse:
    video_id = request.GET.get("video")
    rules = CommentKeywordRule.objects.select_related("video").order_by("-priority", "keyword")
    if video_id:
        rules = rules.filter(video_id=video_id)
    return render(
        request,
        "panel/rules/list.html",
        {
            "rules": rules,
            "videos": VideoPost.objects.order_by("-updated_at"),
            "selected_video": video_id,
        },
    )


@login_required(login_url="panel_login")
@require_http_methods(["GET", "POST"])
def rule_create(request: HttpRequest) -> HttpResponse:
    initial = {}
    video_id = request.GET.get("video")
    if video_id:
        initial["video"] = video_id
    form = CommentKeywordRuleForm(request.POST or None, initial=initial)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Qoida qo'shildi")
        return redirect("panel_rule_list")
    return render(request, "panel/rules/form.html", {"form": form, "title": "Yangi qoida"})


@login_required(login_url="panel_login")
@require_http_methods(["GET", "POST"])
def rule_edit(request: HttpRequest, pk: int) -> HttpResponse:
    rule = get_object_or_404(CommentKeywordRule, pk=pk)
    form = CommentKeywordRuleForm(request.POST or None, instance=rule)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Qoida yangilandi")
        return redirect("panel_rule_list")
    return render(
        request,
        "panel/rules/form.html",
        {"form": form, "title": "Qoidani tahrirlash", "rule": rule},
    )


@login_required(login_url="panel_login")
@require_POST
def rule_delete(request: HttpRequest, pk: int) -> HttpResponse:
    rule = get_object_or_404(CommentKeywordRule, pk=pk)
    rule.delete()
    messages.success(request, "Qoida o'chirildi")
    return redirect("panel_rule_list")


@login_required(login_url="panel_login")
@require_POST
def rule_toggle(request: HttpRequest, pk: int) -> HttpResponse:
    rule = get_object_or_404(CommentKeywordRule, pk=pk)
    rule.is_active = not rule.is_active
    rule.save(update_fields=["is_active", "updated_at"])
    return redirect("panel_rule_list")


@login_required(login_url="panel_login")
def product_list(request: HttpRequest) -> HttpResponse:
    q = request.GET.get("q", "").strip()
    products = Product.objects.all().order_by("product_name")
    if q:
        products = products.filter(product_name__icontains=q)
    products = products[:100]
    return render(request, "panel/products/list.html", {"products": products, "q": q})
