from django import template

register = template.Library()


@register.simple_tag(takes_context=True)
def url_replace(context, **kwargs):
    """Replace or append query string parameters without duplicate keys (e.g., page)."""
    request = context.get("request")
    if not request or not hasattr(request, "GET"):
        return "&".join(f"{k}={v}" for k, v in kwargs.items() if v is not None and v != "")

    query = request.GET.copy()
    for key, value in kwargs.items():
        if value is None or value == "":
            query.pop(key, None)
        else:
            query[key] = str(value)
    return query.urlencode()
