from django import template
from django.urls import reverse

register = template.Library()


@register.filter()
def seconds_to_long_time(value):
    total_minutes, seconds = divmod(value, 60)
    total_hours, minutes = divmod(total_minutes, 60)
    total_days, hours = divmod(total_hours, 24)
    if total_days:
        return '%d:%02d:%02d' % (total_days, hours, minutes)
    else:
        return '%d:%02d' % (total_hours, minutes)


@register.filter()
def get_url_enemy_no_filter(value, arg):
    bucket = value

    return ''


@register.filter()
def get_url_enemy_juiced(value, arg):
    return ''
