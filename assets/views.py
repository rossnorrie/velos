from django.shortcuts import render
from rest_framework import viewsets
from .models import asset, lease, documentz, similarityz
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
def tree_report_view(request):
    sims = similarityz.objects.all()

    def get_bucket(score):
        # Convert score to a bucket label like "00-09%"
        bucket = int((score or 0.0) * 100) // 10 * 10
        return f"{bucket:02d}-{bucket + 9}%"

    # Use defaultdict to build the grouped data and chart data
    grouped = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    chart_data = defaultdict(lambda: defaultdict(int))

    for sim in sims:
        source = sim.doc1_id.file_name
        destination = sim.doc2_id.file_name

        for sim_type in ['text', 'meta', 'image', 'overall']:
            sim_value = getattr(sim, f"{sim_type}_sim", 0.0) or 0.0
            bucket = get_bucket(sim.overall_sim)
            grouped[source][sim_type.capitalize()][bucket].append({
                'destination': destination,
                'destination_icon': sim.doc2_id.file_name,
                'meta_sim': sim.meta_sim or 0.0,
                'text_sim': sim.text_sim or 0.0,
                'image_sim': sim.image_sim or 0.0,
                'overall_sim': sim.overall_sim or 0.0,
                'doc1_text': sim.doc1_id.text_contents,
                'doc2_text': sim.doc2_id.text_contents,
            })
            chart_data[source][f"{sim_type}_{bucket}"] += 1

    similarity_headers = [
        {"label": "Meta Sim", "id": "meta", "icon": "fa-info-circle"},
        {"label": "Text Sim", "id": "text", "icon": "fa-font"},
        {"label": "Image Sim", "id": "image", "icon": "fa-image"},
        {"label": "Overall Sim", "id": "overall", "icon": "fa-globe"},
    ]

    # Create a sorted list of threshold values (as floats) and then
    # derive the bucket order labels from them.
    threshold_values = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]
    threshold_values = sorted(threshold_values)
    bucket_order = [get_bucket(th) for th in threshold_values]

    # For each source and similarity type, re-order the buckets based on bucket_order
    for source, sim_types in grouped.items():
        for sim_type, buckets in sim_types.items():
            sorted_buckets = OrderedDict()
            for bucket in bucket_order:
                if bucket in buckets:
                    sorted_buckets[bucket] = buckets[bucket]
            grouped[source][sim_type] = sorted_buckets

    # Pass bucket_order to the template if you need to iterate in that order
    return render(request, 'assets/gen_report.html', {
        'grouped': to_dict(grouped),
        'chart_data': to_dict(chart_data),
        'similarity_headers': similarity_headers,
        'threshold_values': threshold_values,
        'bucket_order': bucket_order,
    })

@login_required
def gen_report(request):
    # Get all similarity records from your model.
    sims = similarityz.objects.all()
    
    # Define header information for each similarity metric.
    similarity_headers = [
        {"label": "Meta Sim", "id": "meta"},
        {"label": "Text Sim", "id": "text"},
        {"label": "Image Sim", "id": "image"},
        {"label": "Overall Sim", "id": "overall"}
    ]
    
    # Define the threshold values to populate the dropdown menus.
    # These values will be used in the template for filtering.
    threshold_values = ["0.1", "0.2", "0.3", "0.4", "0.5", "0.6", "0.7", "0.8", "0.9"]

    context = {
        'sims': sims,
        'similarity_headers': similarity_headers,
        'threshold_values': threshold_values,
    }
    return render(request, 'assets/gen_report.html', context)
    
@login_required
def asset_ms_graph_asset_list(request):
    group_by_properties = 'manufacturer, model, operatingSystem, osVersion'  # Customize as needed

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
            top=1000,
            max_retries=None,
            group_by_properties=group_by_properties
        )

        if not devices:
            return render(request, 'assets/error_page.html', {
                'error_message': 'No devices found.'
            })

        if isinstance(devices, list) and all(isinstance(d, dict) for d in devices):
            group_by_properties_list = [h.strip() for h in group_by_properties.split(",")]
            grouped_data = group_devices_recursively(devices, group_by_properties_list)
            grouped_data = add_icon_and_colour(grouped_data)

            # ✅ Fix: Proper JSON serialization for safe JavaScript embedding
            groups_json = mark_safe(json.dumps(grouped_data))

            return render(request, 'assets/generic_report.html', {
                'groups': grouped_data,  # used in template rendering
                'groups_json': mark_safe(json.dumps(grouped_data)),  # used for JS
                'header_list': group_by_properties_list,
            })
        else:
            return render(request, 'assets/error_page.html', {
                'error_message': 'The data structure is not a list of dictionaries as expected.'
            })

    except Exception as e:
        return render(request, 'assets/error_page.html', {
            'error_message': f'An error occurred: {e}'
        })

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
        }

        # Assign unique color for top-level groups (level 0)
        if level == 0:
            group_entry["colour"] = color_palette[i % len(color_palette)]

        if subgroup:
            group_entry["sub_groups"] = subgroup

        result.append(group_entry)

    return result

def add_icon_and_colour(groups):
    """
    Recursively injects icon and colour values into each group.
    """
    for group in groups:
        group_by = group.get("group_by", "").lower()
        value = (group.get("value") or "").strip().lower()

        if group_by == "operatingSystem":
            if value == "windows":
                group["icon"] = "fab fa-windows"
                group["colour"] = "#1f77b4"
            elif value == "macos":
                group["icon"] = "fab fa-apple"
                group["colour"] = "#d62728"
            else:
                group["icon"] = "fas fa-question-circle"
                group["colour"] = "#8c564b"
        elif group_by == "osVersion":
            group["icon"] = "fas fa-desktop"
            group["colour"] = "#ff7f0e"
        else:
            group["icon"] = "fas fa-folder"

        if group.get("sub_groups"):
            add_icon_and_colour(group["sub_groups"])

    return groups
        
def asset_ms_graph_asset_list2(request):
    group_by_properties = 'manufacturer, model'
    
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
            top=1000,
            max_retries=None,
            group_by_properties=group_by_properties
        )

        # Debugging: print devices to check if data is correctly fetched
        print(devices)

        if not devices:  # Check if no devices were returned
            print("No devices found")  # Debugging
            return render(request, 'assets/error_page.html', {
                'error_message': 'No devices found.'
            })

        def add_icon_and_colour(groups):
            """
            Recursively injects icon and colour values into each group.
            """
            for group in groups:
                group_by = group.get("group_by", "")
                value = (group.get("value") or "").strip().lower()
                if group_by == "operatingSystem":
                    if value == "windows":
                        group["icon"] = "fab fa-windows"
                        group["colour"] = "#1f77b4"
                    elif value == "macos":
                        group["icon"] = "fab fa-apple"
                        group["colour"] = "#d62728"
                    else:
                        group["icon"] = "fas fa-question-circle"
                        group["colour"] = "#8c564b"
                elif group_by == "osVersion":
                    group["icon"] = "fas fa-desktop"
                    group["colour"] = "#ff7f0e"
                # Process sub-groups recursively if present
                if group.get("sub_groups"):
                    add_icon_and_colour(group["sub_groups"])
            return groups

        # Add icon and colour info to the grouping data.
        devices = add_icon_and_colour(devices)

        # Check the data after adding icons/colors
        print(devices)  # Debugging

        header_list = [h.strip() for h in group_by_properties.split(",")]

        return render(request, 'assets/generic_report.html', {
            'groups': devices,
            'header_list': header_list,
        })
    
    except Exception as e:
        print(f"Error: {e}")  # Log the error
        return render(request, 'assets/error_page.html', {
            'error_message': 'An error occurred while fetching the devices.'
        })


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
        accountType='Member'
    )

    if users:
        return render(request, 'assets/ms_graph_list.html', {'users': users})

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
        accountType='Member'
    )

    if users:
        return render(request, 'assets/orbit.html', {'people_data': users})
