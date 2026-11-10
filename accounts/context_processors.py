def user_role(request):
    """
    متغیرهای مربوط به نقش کاربر برای استفاده در قالب‌ها:
    - is_manager: آیا کاربر فعلی مدیر است یا خیر
    - is_seller: آیا کاربر فعلی فروشنده است یا خیر
    - active_role: شناسه نقش ('manager' یا 'seller')
    - active_role_display: عنوان فارسی نقش ('مدیر' یا 'فروشنده')
    """
    if not hasattr(request, "user") or not request.user.is_authenticated:
        return {
            "is_manager": False,
            "is_seller": False,
            "active_role": None,
            "active_role_display": "",
        }

    user = request.user
    profile = getattr(user, "profile", None)

    is_manager = user.is_superuser or (profile is not None and profile.role == "manager")
    is_seller = not is_manager

    return {
        "is_manager": is_manager,
        "is_seller": is_seller,
        "active_role": "manager" if is_manager else "seller",
        "active_role_display": "مدیر" if is_manager else "فروشنده",
    }
