from django import template
from django.forms import CheckboxSelectMultiple

register = template.Library()

@register.filter(name='add_class')
def add_class(field, css_class):
    return field.as_widget(attrs={"class": css_class, "placeholder": " "})

@register.filter
def is_checkboxselectmultiple(field):
    return isinstance(field.field.widget, CheckboxSelectMultiple)