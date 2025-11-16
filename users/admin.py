from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _
from .models import *

class UserAdmin(BaseUserAdmin):
    # Fields to display in the admin interface
    list_display = ('email', 'is_staff', 'is_superuser', 'is_active')
    list_filter = ('is_staff', 'is_superuser', 'is_active')
    
    # Fieldsets for organizing the form in the admin interface
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        (_('Permissions'), {'fields': ('is_staff', 'is_superuser', 'is_active')}),
        (_('Important dates'), {'fields': ('last_login',)}),
    )
    
    # Fields for creating a new user in the admin interface
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2', 'is_staff', 'is_superuser', 'is_active'),
        }),
    )
    
    # Configurations for searching and ordering
    search_fields = ('email',)
    ordering = ('email',)
    filter_horizontal = ()

# Register the User model with the custom admin
admin.site.register(User, UserAdmin)


@admin.register(UserOpenAccount)
class UserOpenAccountAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "ip_address", "device", "browser", "os", "first_seen_at", "last_seen_at", "status")
    list_filter = ("status", "os", "browser", "device", "first_seen_at")
    search_fields = ("id", "ip_address", "user_agent", "device", "browser", "os")
    readonly_fields = ("id", "first_seen_at", "last_seen_at")

    fieldsets = (
        ("User Info", {"fields": ("id", "ip_address", "user_agent")}),
        ("Device Details", {"fields": ("device", "browser", "os")}),
        ("Activity", {"fields": ("first_seen_at", "last_seen_at")}),
        ("Status", {"fields": ("status",)}),
    )
    
@admin.register(UserActivityLog)
class UserActivityLogAdmin(admin.ModelAdmin):
    list_display = ("user", "url", "timestamp")  # Columns to show in the list view
    search_fields = ("user__id", "url")  # Searchable fields
    list_filter = ("timestamp",)  # Filters for date/time
    ordering = ("-timestamp",)