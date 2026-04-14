from django.contrib import admin
from .models import (
    Category,
    Product,
    ProductImage,
    ProductVariant,
    ProductVariantImage,
    Review,
)


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1


class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 0
    fields = ("color_name", "size_name", "sku", "price", "stock_status", "is_active")


class ProductVariantImageInline(admin.TabularInline):
    model = ProductVariantImage
    extra = 1


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "slug", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "category", "price", "is_new", "stock_status")
    list_filter = ("category", "is_new", "stock_status")
    search_fields = ("name",)
    inlines = [ProductImageInline, ProductVariantInline]


@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display = ("id", "product", "color_name", "size_name", "price", "stock_status", "is_active")
    list_filter = ("stock_status", "is_active", "product__category")
    search_fields = ("product__name", "color_name", "size_name", "sku")
    inlines = [ProductVariantImageInline]


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "phone", "is_approved", "created_at")
    list_filter = ("is_approved", "created_at")
    search_fields = ("name", "phone", "text")