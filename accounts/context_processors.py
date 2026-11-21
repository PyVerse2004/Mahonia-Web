def user_role(request):
    """
    Context processor providing user role flags and identifiers for templates:
    - is_manager: True if the current user has manager privileges or is superuser
    - is_seller: True if the current user is restricted to seller role
    - active_role: Role identifier ('manager' or 'seller')
    - active_role_display: Persian display label ('مدیر' or 'فروشنده')
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
