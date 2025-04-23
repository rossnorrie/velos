from django.shortcuts import render
from rest_framework import viewsets
from .models import asset, lease, documentz, similarityz, report_categories, reports, ClassificationDetail
from .serializers import AssetSerializer, LeaseSerializer
import asyncio
import configparser
from ms_graph import ms_graph_toolkit  
from ms_graph import iutils
from ms_graph import maria_db
from datetime import datetime
import json
from collections import defaultdict, OrderedDict
import pprint
from django.contrib.auth.decorators import login_required
from collections import defaultdict
from django.shortcuts import render
from django.utils.safestring import mark_safe
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
import uuid
from collections import defaultdict, Counter
from django.http import HttpResponseBadRequest
from django.apps import apps
from django.db.models import Q





def to_dict(obj):
    if isinstance(obj, defaultdict):
        return {k: to_dict(v) for k, v in obj.items()}
    return obj

def get_bucket(score):
    bucket = int((score or 0.0) * 100) // 10 * 10
    return f"{bucket:02d}-{bucket + 9:02d}%"


class AssetViewSet(viewsets.ModelViewSet):
    queryset = asset.objects.all()
    serializer_class = AssetSerializer

class LeaseViewSet(viewsets.ModelViewSet):
    queryset = lease.objects.all()
    serializer_class = LeaseSerializer

@login_required
def asset_list(request):
    assets = asset.objects.all()
    return render(request, 'assets/asset_list.html', {'assets': assets})

@login_required
def doc_list(request):
    docz = documentz.objects.all()
    return render(request, 'assets/doc_list.html', {'docz': docz})

@login_required
def doc_sim(request):
    sims = similarityz.objects.all()
    similarity_headers = [
        {"label": "Meta Sim", "id": "meta"},
        {"label": "Text Sim", "id": "text"},
        {"label": "Image Sim", "id": "image"},
        {"label": "Overall Sim", "id": "overall"}
    ]
    #threshold_values = ["0.1", "0.2", "0.3", "0.4", "0.5", "0.6", "0.7", "0.8", "0.9"]
    threshold_values = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]
    threshold_values = sorted(threshold_values) 
    return render(request, 'assets/doc_sim.html', {
        'sims': sims,
        'similarity_headers': similarity_headers,
        'threshold_values': threshold_values
    })


    
@login_required
def asset_ms_graph_asset_list(request, group_by_properties=None, header_text=None):
    # Parse group_by_properties from query string if not passed as URL param
    group_by_properties = group_by_properties or request.GET.get("tree_view")
    report_name = header_text or request.GET.get("report_name")
    # Retrieve additional query parameters for report properties.
    report_description = request.GET.get("report_description")
    report_icon = request.GET.get("report_icon")



    grouping_fields = []
    if group_by_properties:
        print("Raw group_by_properties:", group_by_properties)
        # Split and validate
        grouping_fields = [field.strip() for field in group_by_properties.split(",")]
        #grouping_fields = [f for f in grouping_fields if f in VALID_FIELDS]
        print("Validated grouping_fields:", grouping_fields)

    # Reconstruct cleaned group_by_properties string
    cleaned_group_by_properties = ",".join([str(g) for g in grouping_fields if g is not None])

    #if not grouping_fields:
    #    return render(request, 'assets/error_page.html', {
    #        'error_message': 'No valid grouping fields provided.'
    #    })

    # Initialize your MSGraphClient
    client = ms_graph_toolkit.MSGraphClient(
        tenant_id="42fd9015-de4d-4223-a368-baeacab48927",
        client_id="2bc1c9b9-d0ad-4ff1-ac90-f5f54f942efb",
        client_secret="o5B8Q~XnkYM_BFpZ3anY~5lzrSiVqqGW3P_60br1",
        baseline="1"
    )

    try:
        devices = client.query_devices_extended(
            email=None,
            start_date=None,
            end_date=None,
            top=None,
            max_retries=None,
            group_by_properties=cleaned_group_by_properties
        )

        if not devices:
            return render(request, 'assets/error_page.html', {
                'error_message': 'No devices found.'
            })

        if isinstance(devices, list) and all(isinstance(d, dict) for d in devices):
            # Group and enhance the data
            full_grouped_data = group_devices_recursively(devices, grouping_fields)
            full_grouped_data = add_icon_and_colour(full_grouped_data)

            # --- Pagination: Only paginate the top-level groups ---
            paginator = Paginator(full_grouped_data, 10)  # 10 groups per page
            page = request.GET.get('page', '1')
            try:
                paged_groups = paginator.page(page)
            except PageNotAnInteger:
                paged_groups = paginator.page(1)
            except EmptyPage:
                paged_groups = paginator.page(paginator.num_pages)

            # Pass the full data for the chart and paginated data for the table,
            # along with the report properties from the query string.
            return render(request, html_name, {
                'groups': paged_groups,  # Paginated groups for table
                'groups_json': mark_safe(json.dumps(full_grouped_data)),  # Full data for chart rendering
                'header_list': grouping_fields,
                'paginator': paginator,
                'report_name': report_name,
                'report_description': report_description,
                'report_icon': report_icon,
            })
        else:
            return render(request, 'assets/error_page.html', {
                'error_message': 'The data structure is not a list of dictionaries as expected.'
            })

    except Exception as e:
        return render(request, 'assets/error_page.html', {
            'error_message': f'An error occurred: {e}'
        })
        

def asset_ms_graph_user_list_generic(request, group_by_properties=None, header_text=None):
    group_by_properties = group_by_properties or request.GET.get("tree_view")
    report_name = header_text or request.GET.get("report_name")
    report_description = request.GET.get("report_description")
    report_icon = request.GET.get("report_icon")

    grouping_fields = []
    if group_by_properties:
        print("Raw group_by_properties:", group_by_properties)
        grouping_fields = [field.strip() for field in group_by_properties.split(",")]
        print("Validated grouping_fields:", grouping_fields)

    cleaned_group_by_properties = ",".join([str(g) for g in grouping_fields if g is not None])

    # Initialize MSGraphClient
    client = ms_graph_toolkit.MSGraphClient(
        tenant_id="42fd9015-de4d-4223-a368-baeacab48927",
        client_id="2bc1c9b9-d0ad-4ff1-ac90-f5f54f942efb",
        client_secret="o5B8Q~XnkYM_BFpZ3anY~5lzrSiVqqGW3P_60br1",
        baseline="1"
    )

    try:
        users = client.query_users(
            email=None,
            start_date=None,
            end_date=None,
            page_size=100,
            top=100,
            max_retries=5,
            orbit=False,
            presence=False,
            accountType=None, 
            group_by_properties=group_by_properties
        )

        if not users:
            return render(request, 'assets/error_page.html', {
                'error_message': 'No users found.'
            })

        if isinstance(users, list) and all(isinstance(u, dict) for u in users):
            # Group and enhance the data
            full_grouped_data = group_users_recursively(users, grouping_fields)
            full_grouped_data = add_icon_and_colour(full_grouped_data)

            # Paginate top-level user groups
            paginator = Paginator(full_grouped_data, 10)
            page = request.GET.get('page', '1')
            try:
                paged_groups = paginator.page(page)
            except PageNotAnInteger:
                paged_groups = paginator.page(1)
            except EmptyPage:
                paged_groups = paginator.page(paginator.num_pages)

            return render(request, html_name, {
                'groups': paged_groups,
                'groups_json': mark_safe(json.dumps(full_grouped_data)),
                'header_list': grouping_fields,
                'paginator': paginator,
                'report_name': report_name,
                'report_description': report_description,
                'report_icon': report_icon,
            })
        else:
            return render(request, 'assets/error_page.html', {
                'error_message': 'The data structure is not a list of dictionaries as expected.'
            })

    except Exception as e:
        return render(request, 'assets/error_page.html', {
            'error_message': f'An error occurred: {e}'
        })

def group_users_recursively(users, properties, level=0, color_palette=None):
    if not properties:
        return []

    if color_palette is None:
        color_palette = [
            "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd",
            "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf"
        ]

    grouped = defaultdict(list)
    current_property = properties[0]

    for user in users:
        key = user.get(current_property, "(Not Available)")
        grouped[key].append(user)

    result = []
    total_count = len(users)

    for i, (key, items) in enumerate(grouped.items()):
        subgroup = group_users_recursively(items, properties[1:], level + 1, color_palette)

        group_entry = {
            "group_by": current_property,
            "value": key,
            "count": len(items),
            "percentage": (len(items) / total_count) * 100 if total_count else 0,
        }

        if level == 0:
            group_entry["colour"] = color_palette[i % len(color_palette)]

        if subgroup:
            group_entry["sub_groups"] = subgroup

        result.append(group_entry)

    return result
        
@login_required        
def asset_ms_graph_asset_list(request, group_by_properties=None):
    # Parse group_by_properties from query string if not passed as URL param
    group_by_properties = group_by_properties or request.GET.get("tree_view")

    grouping_fields = []
    if group_by_properties:
        print("Raw group_by_properties:", group_by_properties)
        # Split and validate
        grouping_fields = [field.strip() for field in group_by_properties.split(",")]
        #grouping_fields = [f for f in grouping_fields if f in VALID_FIELDS]
        print("Validated grouping_fields:", grouping_fields)

    # Reconstruct cleaned group_by_properties string
    cleaned_group_by_properties = ",".join([str(g) for g in grouping_fields if g is not None])

    #if not grouping_fields:
    #    return render(request, 'assets/error_page.html', {
    #        'error_message': 'No valid grouping fields provided.'
    #    })

    # Initialize your MSGraphClient
    client = ms_graph_toolkit.MSGraphClient(
        tenant_id="42fd9015-de4d-4223-a368-baeacab48927",
        client_id="2bc1c9b9-d0ad-4ff1-ac90-f5f54f942efb",
        client_secret="o5B8Q~XnkYM_BFpZ3anY~5lzrSiVqqGW3P_60br1",
        baseline="1"
    )

    try:
        devices = client.query_devices_extended(
            email=None,
            start_date=None,
            end_date=None,
            top=None,
            max_retries=None,
            group_by_properties=cleaned_group_by_properties
            
        )

        if not devices:
            return render(request, 'assets/error_page.html', {
                'error_message': 'No devices found.'
            })

        if isinstance(devices, list) and all(isinstance(d, dict) for d in devices):
            grouped_data = group_devices_recursively(devices, grouping_fields)
            grouped_data = add_icon_and_colour(grouped_data)

            return render(request, 'assets/generic_report.html', {
                'groups': grouped_data,
                'groups_json': mark_safe(json.dumps(grouped_data)),
                'header_list': grouping_fields,
            })
        else:
            return render(request, 'assets/error_page.html', {
                'error_message': 'The data structure is not a list of dictionaries as expected.'
            })

    except Exception as e:
        return render(request, 'assets/error_page.html', {
            'error_message': f'An error occurred: {e}'
        })



###########################################################################
def group_devices_recursively(devices, properties, level=0, color_palette=None):
    if not properties:
        return []

    if color_palette is None:
        color_palette = [
            "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd",
            "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf"
        ]

    grouped = defaultdict(list)
    current_property = properties[0]

    for device in devices:
        key = device.get(current_property, "(Not Available)")
        grouped[key].append(device)

    result = []
    total_count = len(devices)

    for i, (key, items) in enumerate(grouped.items()):
        subgroup = group_devices_recursively(items, properties[1:], level + 1, color_palette)

        group_entry = {
            "group_by": current_property,
            "value": key,
            "count": len(items),
            "percentage": (len(items) / total_count) * 100 if total_count else 0,
            "sub_groups": subgroup  # ✅ always include this
        }

        if level == 0:
            group_entry["colour"] = color_palette[i % len(color_palette)]

        result.append(group_entry)

    return result

     
def add_icon_and_colour(groups, mapping=None, default_icon="fas fa-folder", default_colour="#cccccc"):
    """
    Recursively injects icon and colour values into each group.
    
    :param groups: List of group dictionaries to process. Each group should have keys like "group_by" and "value",
                   and optionally a "sub_groups" key with a list of further groups.
    :param mapping: Optional dictionary mapping lower-case group_by keys to a sub-dictionary that maps values to 
                    (icon, colour) tuples. It can include a "default" entry for unknown values.
                    For example:
                        {
                          "operatingsystem": {
                              "windows": ("fab fa-windows", "#1f77b4"),
                              "macos": ("fab fa-apple", "#d62728"),
                              "default": ("fas fa-question-circle", "#8c564b")
                          },
                          "osversion": {
                              "default": ("fas fa-desktop", "#ff7f0e")
                          }
                        }
    :param default_icon: Global default icon if group_by is not found in mapping.
    :param default_colour: Global default colour if group_by is not found in mapping.
    :returns: The updated groups with added "icon" and "colour" keys.
    """
    
    if mapping is None:
        # Define a default mapping if one isn't provided.
        mapping = {
            "operatingsystem": {
                "windows": ("fab fa-windows", "#1f77b4"),
                "macos": ("fab fa-apple", "#d62728"),
                "default": ("fas fa-question-circle", "#8c564b")
            },
            "osversion": {
                "default": ("fas fa-desktop", "#ff7f0e")
            }
        }

    for group in groups:
        # Safely get the text values for grouping key and its value.
        group_by = (group.get("group_by") or "").strip().lower()
        value = (group.get("value") or "").strip().lower()
        
        if group_by in mapping:
            value_mapping = mapping[group_by]
            # If the value is explicitly mapped use it; otherwise, use the group-specific default if available.
            if value in value_mapping:
                icon, colour = value_mapping[value]
            else:
                icon, colour = value_mapping.get("default", (default_icon, default_colour))
        else:
            # Fallback to the global defaults.
            icon, colour = (default_icon, default_colour)
        
        group["icon"] = icon
        group["colour"] = colour
        
        # If sub_groups exist and is a list, process them recursively.
        sub_groups = group.get("sub_groups")
        if isinstance(sub_groups, list):
            add_icon_and_colour(sub_groups, mapping, default_icon, default_colour)
   
    return groups
   



@login_required
def asset_ms_graph_user_list(request):
    client = ms_graph_toolkit.MSGraphClient(
        tenant_id="42fd9015-de4d-4223-a368-baeacab48927",
        client_id="2bc1c9b9-d0ad-4ff1-ac90-f5f54f942efb",
        client_secret="o5B8Q~XnkYM_BFpZ3anY~5lzrSiVqqGW3P_60br1",
        baseline="1"
    )

    users = client.query_users(
        email=None,
        start_date=None,
        end_date=None,
        top=100,
        max_retries=None,
        accountType='Member',
        group_by_properties=group_by_properties
    )

    if users:
        return render(request, 'assets/generic_report.html', {'users': users})

@login_required
def asset_ms_graph_user_orbit(request):
    client = ms_graph_toolkit.MSGraphClient(
        tenant_id="42fd9015-de4d-4223-a368-baeacab48927",
        client_id="2bc1c9b9-d0ad-4ff1-ac90-f5f54f942efb",
        client_secret="o5B8Q~XnkYM_BFpZ3anY~5lzrSiVqqGW3P_60br1",
        baseline="1"
    )

    users = client.query_users(
        email=None,
        start_date=None,
        end_date=None,
        top=100,
        page_size=100,
        max_retries=5,
        orbit=True,
        presence=False,
        accountType='Member',
        group_by_properties=group_by_properties
    )

    if users:
        return render(request, 'assets/orbit.html', {'people_data': users})


@login_required
def report_dashboard(request):


    reports = report_categories.objects.all()

    return render(request, 'assets/report_dashboard.html', {
        'reports': reports,

    })
##############################################################################################
def generic_ms_graph_user(request, group_by_properties=None):
    group_by_properties = request.GET.get("tree_view", "")
    report_name = request.GET.get("report_name", "Report")
    html_name = request.GET.get("html_name")
    
    try:
        data, grouping_fields = generic_report_msgraph_data(
            query_func=lambda client, **kwargs: client.query_users(**kwargs),
            query_kwargs={
                "email": None,
                "start_date": None,
                "end_date": None,
                "page_size": 100,
                "top": 100,
                "max_retries": 5,
                "orbit": False,
                "presence": False,
                "accountType": None,
                "group_by_properties": group_by_properties
                
            },
            group_by_properties=group_by_properties
        )
        
        return generic_grouped_report_renderer(
            request=request,
            data=data,
            grouping_fields=grouping_fields,
            header_text= report_name
        )

    except ValueError as ve:
        return render(request, 'assets/error_page.html', {'error_message': str(ve)})
    except Exception as e:
        return render(request, 'assets/error_page.html', {'error_message': f'Unexpected error: {e}'})
    
def generic_ms_graph_device(request, group_by_properties=None):
    group_by_properties = request.GET.get("tree_view", "")
    report_name = request.GET.get("report_name", "Report")
    html_name = request.GET.get("html_name")

    try:
        data, grouping_fields = generic_report_msgraph_data(
            query_func=lambda client, **kwargs: client.query_devices_extended(**kwargs),
            query_kwargs={
                "email": None,
                "start_date": None,
                "end_date": None,
                "page_size": 100,
                "top": 100,
                "max_retries": 5,
                "device_name":None,
                "group_by_properties": group_by_properties
                
            },
            group_by_properties=group_by_properties
        )
            
        
        print(data, grouping_fields)
        return generic_grouped_report_renderer(
            request=request,
            data=data,
            grouping_fields=grouping_fields,
            header_text=report_name
            
            

        )

    except ValueError as ve:
        return render(request, 'assets/error_page.html', {'error_message': str(ve)})
    except Exception as e:
        return render(request, 'assets/error_page.html', {'error_message': f'Unexpected error: {e}'})   


def get_valid_fields(model, prefix="", depth=3):
    """
    Recursively collects valid field paths for the given model.
    Limits to `depth` levels of relationships to avoid infinite recursion.
    """
    valid_fields = get_valid_fields(model)

    if depth <= 0:
        return valid_fields

    for field in model._meta.get_fields():
        if field.auto_created and not field.concrete:
            continue  # Skip reverse relations unless you want prefetch_related

        if field.is_relation and hasattr(field, "related_model"):
            # Go deeper into related model
            nested_prefix = f"{prefix}{field.name}__"
            valid_fields |= get_valid_fields(field.related_model, nested_prefix, depth - 1)
        else:
            valid_fields.add(f"{prefix}{field.name}")

    return valid_fields


##############################################################################################
# Updated MSGraph Data Fetching Function
def get_valid_fields(model, prefix="", depth=3, visited=None):
    if visited is None:
        visited = set()

    model_id = f"{model._meta.app_label}.{model.__name__}"
    if model_id in visited or depth <= 0:
        return set()

    visited.add(model_id)
    valid_fields = set()

    for field in model._meta.get_fields():
        if field.auto_created and not field.concrete:
            continue
        if field.is_relation and hasattr(field, "related_model"):
            try:
                related_model = field.related_model
                nested_prefix = f"{prefix}{field.name}__"
                valid_fields |= get_valid_fields(related_model, nested_prefix, depth - 1, visited.copy())
            except Exception:
                continue
        else:
            valid_fields.add(f"{prefix}{field.name}")
    return valid_fields

##############################################################################################
# Updated MSGraph Data Fetching Function
def generic_report_msgraph_data(query_func, query_kwargs, group_by_properties):
     client = ms_graph_toolkit.MSGraphClient(
         tenant_id="42fd9015-de4d-4223-a368-baeacab48927",
         client_id="2bc1c9b9-d0ad-4ff1-ac90-f5f54f942efb",
         client_secret="o5B8Q~XnkYM_BFpZ3anY~5lzrSiVqqGW3P_60br1",
         baseline="1"
     )
 
     data = query_func(client, **query_kwargs)
 
     if not data:
         raise ValueError('Invalid or no data returned from MS Graph.')
 
     # Prepare grouping fields (each field is stripped of whitespace)
     grouping_fields = [field.strip() for field in group_by_properties.split(",") if field.strip()]
 
     grouped_data = recursive_grouping(data, grouping_fields)
 
     enhanced_data = add_icon_and_colour(grouped_data)
 
     return enhanced_data, grouping_fields

    

@login_required
def generic_db(request, group_by_properties=None):
    model_name = request.GET.get("model_name")  # e.g., "Documentz"
    html_name = request.GET.get("html_name")
    tree_view = request.GET.get("tree_view")  # e.g., "category,extension"
    report_name = request.GET.get("report_name", "Report")

    if not model_name or not tree_view:
        return HttpResponseBadRequest("Missing required parameters: model and tree_view")

    try:
        # Load model from assets app
        Model = apps.get_model(app_label="assets", model_name=model_name)
        if not Model:
            return HttpResponseBadRequest("Model not found")

        # Build valid fields (direct + 1-level related lookups)
        valid_fields = get_valid_fields(Model)

        # Process and validate grouping fields
        raw_grouping_fields = [f.strip() for f in tree_view.split(",") if f.strip()]
        grouping_fields = [f for f in raw_grouping_fields if f in valid_fields]
        if not grouping_fields:
            return HttpResponseBadRequest("No valid fields found in tree_view")

        print("=== VALID FIELDS ===")
        for field in sorted(valid_fields):
            print(field)

        print("=== RAW GROUPING FIELDS ===")
        print(raw_grouping_fields)
        # Reserved query params (not used for filtering)
        reserved = {
            "model", "model_name", "tree_view", "report_name",
            "report_description", "report_icon", "html_name"
        }

        # Filter params that match valid fields only
        filters = {
            k: v for k, v in request.GET.items()
            if k not in reserved and k in valid_fields and v
        }

        # Build Q object for filtering
        q_object = Q()
        for key, value in filters.items():
            q_object &= Q(**{key: value})

        # Perform the query
        #queryset = list(Model.objects.filter(q_object).values(*grouping_fields))
        #queryset = list(Model.objects.all().values(*grouping_fields))
        # Determine related lookups to optimize joins (only parent lookups for now)
        related_lookups = set()
        for field in grouping_fields:
            parts = field.split("__")
            if len(parts) > 1:
                related_lookups.add("__".join(parts[:-1]))

        # Perform the query with related data included
        queryset = list(
            Model.objects.filter(q_object)
            .select_related(*related_lookups)  # Enables access to FK fields
            .values(*grouping_fields)
        )        

        if not queryset:
            return render(request, 'assets/error_page.html', {
                'error_message': 'No data found for the given filters.'
            })

        # Group and enrich data
        grouped_data = group_devices_recursively(queryset, grouping_fields)
        grouped_data = add_icon_and_colour(grouped_data)
        
        # Render report
        return generic_grouped_report_renderer(
            request=request,
            data=grouped_data,
            grouping_fields=grouping_fields,
            header_text=report_name,
            report_description=request.GET.get("report_description", ""),
            report_icon=request.GET.get("report_icon", "fa-solid fa-chart-bar")
        )




    except LookupError:
        return HttpResponseBadRequest("Invalid model specified")
    except Exception as e:
        return render(request, 'assets/error_page.html', {
            'error_message': f'An error occurred: {e}'
        })
##############################################################################################
# Updated Grouped Report Rendering Function
def generic_grouped_report_renderer(request, data, grouping_fields, header_text=None, report_description="", report_icon="fa-solid fa-chart-bar"):
    report_name = header_text or request.GET.get("report_name", "Report")
    report_description = request.GET.get("report_description", "")
    html_name = request.GET.get("html_name")
    report_icon = request.GET.get("report_icon", "fa-solid fa-chart-bar")
    pagesize = [10, 25, 50, 100, 250, 500]
    
    paginator = Paginator(data, 10)
    page = request.GET.get('page', '1')
    print("paged_groups: " + page)
    try:
        paged_groups = paginator.page(page)
    except PageNotAnInteger:
        paged_groups = paginator.page(1)
    except EmptyPage:
        paged_groups = paginator.page(paginator.num_pages)


    context = {
        'groups': paged_groups,
        'groups_json': mark_safe(json.dumps(data)),
        'header_list': grouping_fields,
        'paginator': paginator,
        'report_name': report_name,
        'report_description': report_description,
        'report_icon': report_icon,
        'page_sizes' : pagesize,
        "action_icons": {
        "downloadCSV": "fa-file-csv",
        "downloadJSON": "fa-file-code",
        "exportTableToPDF": "fa-file-pdf",
        "printReport": "fa-print"
        }
    }
    
    try:

        rend = render(request, html_name, context)
        
        return rend
    except Exception as e:
        print("Error rendering the template: ", e)
        rend = render(request, 'assets/error_page.html', {'error_message': str(e)})
        return rend


##############################################################################################
# Updated Recursive Grouping Utility
def recursive_grouping(items, properties, level=0, color_palette=None):
    if not properties:
        return []
    
    if color_palette is None:
        color_palette = [
            "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd",
            "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf"
        ]
    
    try:
        grouped = defaultdict(list)
        current_property = properties[0]
        for item in items:
            # Use a default if the value is None or falsy.
            key = item.get(current_property) or "(Not Available)"
            grouped[key].append(item)
        
        result = []
        total_count = len(items)
        for i, (key, group_items) in enumerate(grouped.items()):
            # Recursively build any sub-groups
            subgroup = recursive_grouping(group_items, properties[1:], level + 1, color_palette)

            # Add a unique id to each group entry using uuid4.
            group_entry = {
                "id": str(uuid.uuid4()),
                "group_by": current_property,
                "value": key,
                "count": len(group_items),
                "percentage": (len(group_items) / total_count) * 100 if total_count else 0,
            }
            if level == 0:
                group_entry["colour"] = color_palette[i % len(color_palette)]
            if subgroup:
                group_entry["sub_groups"] = subgroup

            result.append(group_entry)
    except Exception as exc:
        print(f"Error during grouping: {exc}")
        return []

    return result


##############################################################################################
# Updated Helper Function to Add Icons and Colours
def add_icon_and_colour(grouped_data):
    # Example mapping for group "value" to an icon.
    icon_mapping = {
        "(not available)": "fa-ban",
        "active": "fa-check-circle",
        "inactive": "fa-times-circle",
        # Add any additional mappings as needed.
    }
    default_icon = "fa-default-icon"

    for group in grouped_data:
        # Safely convert the group "value" to a string and use a default if None.
        value = group.get("value")
        value_str = str(value) if value is not None else "(Not Available)"
        group["icon"] = icon_mapping.get(value_str.lower(), default_icon)
        
        # Recursively process any sub-groups.
        if "sub_groups" in group:
            add_icon_and_colour(group["sub_groups"])
    
    return grouped_data

