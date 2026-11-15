# shop/admin.py
from django.contrib import admin
from .models import *
from django.utils.html import format_html

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'created_at']
    search_fields = ['name']

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'base_price', 'stock', 'is_customizable']
    list_filter = ['category', 'is_customizable']
    search_fields = ['name', 'description']



@admin.register(Customization)
class CustomizationAdmin(admin.ModelAdmin):

    list_display = ['product', 'user', 'position', 'design_preview', 'created_at']
    list_filter = ['position']

    def design_preview(self, obj):
        if obj.preview_image:
            return format_html(
                '<img src="{}" width="70" style="border-radius:5px;" />',
                obj.preview_image.url
            )
        return "No Image"

    design_preview.short_description = "Preview"
@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ['user', 'product', 'quantity', 'price', 'added_at']

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'order_date', 'total_amount', 'status', 'payment_status']
    list_filter = ['status', 'payment_status']
    search_fields = ['user__username', 'shipping_address']

@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ['order', 'product', 'quantity', 'price']

@admin.register(ChatHistory)
class ChatHistoryAdmin(admin.ModelAdmin):
    list_display = ['user', 'message', 'created_at']


from .models import Feedback

@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = ['user', 'rating', 'message', 'created_at']
    search_fields = ['user__username', 'message']
    list_filter = ['rating', 'created_at']

from .models import Payment

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'order', 'method', 'status', 'amount', 'created_at']
    list_filter = ['method', 'status']
    search_fields = ['user__username']