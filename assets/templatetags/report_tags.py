from django import template
from django.utils.http import urlencode

register = template.Library()

@register.filter
def report_query_params(report):
    """
    Constructs and returns a URL query string for a report object with the following parameters:
      - tree_view (if report.tree_items exists)
      - report_name
      - report_description
      - report_icon
    All parameters are URL-encoded.
    """
    params = {}
    if hasattr(report, 'tree_items') and report.tree_items:
        params['tree_view'] = report.tree_items
    params['report_name'] = report.name
    params['report_description'] = report.description
    params['report_icon'] = report.report_icon
    return urlencode(params)
