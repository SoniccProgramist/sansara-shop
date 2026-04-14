
from django.contrib import admin
from .models import Order, OrderItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ("product", "price", "quantity", "line_total")
    fields = ("product", "price", "quantity", "line_total")


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "phone", "full_name", "city", "total_price", "status", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("phone", "full_name", "city")
    inlines = [OrderItemInline]


admin.site.register(OrderItem)