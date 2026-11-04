from django import template

register = template.Library()


@register.simple_tag(takes_context=True)
def url_replace(context, **kwargs):
    """جایگزینی یا افزودن پارامتر به کوئری‌استرینگ بدون تکرار کلیدها (مثلاً page)."""
    request = context.get("request")
    if not request or not hasattr(request, "GET"):
        return "&".join(f"{k}={v}" for k, v in kwargs.items() if v is not None)

    query = request.GET.copy()
    for key, value in kwargs.items():
        if value is None:
            query.pop(key, None)
        else:
            query[key] = str(value)
    return query.urlencode()
