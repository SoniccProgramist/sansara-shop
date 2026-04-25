from decimal import Decimal, ROUND_HALF_UP

from django.contrib import admin, messages
from django.db import transaction
from django.shortcuts import render, redirect
from django.urls import path

from .models import (
    Category,
    Product,
    ProductImage,
    ProductVariant,
    ProductVariantImage,
    Review,
)
from .forms import CategoryPriceUpdateForm

def round_price_to_5(value: Decimal) -> Decimal:
    if value <= 0:
        return Decimal("0")

    rounded = (value / Decimal("5")).quantize(Decimal("1"), rounding=ROUND_HALF_UP) * Decimal("5")
    return rounded.quantize(Decimal("1"))


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
    list_display = ("id", "name", "parent", "slug", "is_active")
    list_filter = ("is_active", "parent")
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "bulk-price-update/",
                self.admin_site.admin_view(self.bulk_price_update_view),
                name="products_category_bulk_price_update",
            ),
        ]
        return custom_urls + urls

    def bulk_price_update_view(self, request):
        if not self.has_change_permission(request):
            messages.error(request, "У вас немає прав для зміни цін.")
            return redirect("admin:products_category_changelist")

        form = CategoryPriceUpdateForm(request.POST or None)

        if request.method == "POST" and form.is_valid():
            category = form.cleaned_data["category"]
            percent = form.cleaned_data["percent"]
            fixed_amount = form.cleaned_data.get("fixed_amount")
            update_products = form.cleaned_data["update_products"]
            update_variants = form.cleaned_data["update_variants"]

            updated_products_count = 0
            updated_variants_count = 0

            def calculate_new_price(old_price: Decimal) -> Decimal:
                if percent not in (None, Decimal("0")):
                    raw_price = old_price * (Decimal("1") + (percent / Decimal("100")))
                else:
                    raw_price = old_price + fixed_amount

                new_price = round_price_to_5(raw_price)

                if new_price < 0:
                    new_price = Decimal("0")

                return new_price

            with transaction.atomic():
                if update_products:
                    products = Product.objects.filter(category=category)

                    for product in products:
                        has_variants = product.variants.exists()
                        if not has_variants and product.price is not None:
                            new_price = calculate_new_price(product.price)
                            if new_price < 0:
                                new_price = Decimal("0")

                            product.price = new_price
                            product.save(update_fields=["price"])
                            updated_products_count += 1

                if update_variants:
                    variants = ProductVariant.objects.filter(product__category=category)

                    for variant in variants:
                        if variant.price is not None:
                            new_price = calculate_new_price(variant.price)
                            if new_price < 0:
                                new_price = Decimal("0")

                            variant.price = new_price
                            variant.save(update_fields=["price"])
                            updated_variants_count += 1

            messages.success(
                request,
                f"Ціни оновлено. "
                f"Товарів без варіантів: {updated_products_count}. "
                f"Варіантів: {updated_variants_count}."
            )
            return redirect("admin:products_category_changelist")

        context = {
            **self.admin_site.each_context(request),
            "opts": self.model._meta,
            "title": "Масова зміна цін по категорії",
            "form": form,
        }
        return render(
            request,
            "admin/products/category/bulk_price_update.html",
            context,
        )


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