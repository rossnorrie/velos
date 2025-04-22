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
      - model_name (if not None)
      - html_name (if not None)
    All parameters are URL-encoded.
    """
    params = {}
    if getattr(report, 'tree_items', None):
        params['tree_view'] = report.tree_items
    if getattr(report, 'name', None):
        params['report_name'] = report.name
    if getattr(report, 'description', None):
        params['report_description'] = report.description
    if getattr(report, 'report_icon', None):
        params['report_icon'] = report.report_icon
    if getattr(report, 'model_name', None):
        params['model_name'] = report.model_name
    if getattr(report, 'html_name', None):
        params['html_name'] = report.html_name

    return urlencode(params)
