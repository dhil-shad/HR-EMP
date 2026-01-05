# hr_app/templatetags/hr_extras.py
from django import template
import calendar

register = template.Library()

@register.filter(name='times')
def times(number):
    """Returns a range object of integers from 1 to the number provided."""
    # Used for looping in templates: {% for i in 5|times %}
    return range(1, number + 1)

@register.filter(name='month_name')
def month_name(month_number):
    """Converts a month integer (1-12) to its string name (January-December)."""
    try:
        return calendar.month_name[int(month_number)]
    except (ValueError, IndexError):
        return str(month_number)