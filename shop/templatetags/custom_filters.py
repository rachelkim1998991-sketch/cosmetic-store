from django import template

register=template.Library()

@register.filter
def uz_price(value):
    try:
        value=int(round(float(value)))
    except (ValueError,TypeError):
        return value
    return f"{value:,}".replace(",",".")