from django.contrib import admin
from .models import asset, documentz, lease, similarityz

class AssetAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'purchase_date', 'lease_status', 'price')  # Customize fields shown in the list
    search_fields = ('name', 'category')  # Enable search
    list_filter = ('category', 'lease_status')  # Enable filtering
    ordering = ('-purchase_date',)  # Default sorting

# Register the model with the custom admin class
admin.site.register(asset, AssetAdmin)

