def user_role(request):
    """
    متغیرهای مربوط به نقش کاربر برای استفاده در قالب‌ها:
    - is_manager: آیا کاربر فعلی در نقش مدیر است یا خیر
    - is_seller: آیا کاربر فعلی در نقش فروشنده است یا خیر
    - active_role: نقش فعال ('manager' یا 'seller')
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
    active_role = request.session.get("active_role")
    profile = getattr(user, "profile", None)

    if active_role:
        role = active_role
    elif profile:
        role = profile.role
    elif user.is_superuser:
        role = "manager"
    else:
        role = "seller"

    can_be_manager = user.is_superuser or (profile and profile.role == "manager")
    is_manager = (role == "manager") and can_be_manager
    is_seller = not is_manager

    return {
        "is_manager": is_manager,
        "is_seller": is_seller,
        "active_role": "manager" if is_manager else "seller",
        "active_role_display": "مدیر" if is_manager else "فروشنده",
    }

