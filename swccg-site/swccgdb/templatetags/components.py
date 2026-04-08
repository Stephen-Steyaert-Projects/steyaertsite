from django import template

register = template.Library()


@register.inclusion_tag("components/navbar.html", takes_context=True)
def navbar(context):
    request = context["request"]
    return {
        "current_url_name": request.resolver_match.url_name,
        "user": request.user,
    }
