from products.models import Category, Product

def header_categories(request):
    return {
        "header_categories": Category.objects.filter(is_active=True, parent__isnull=True).order_by("name")
    }

def header_new_products(request):
    return {
        "header_new_products": Product.objects.filter(is_new=True)
        .prefetch_related("images")
        .order_by("-id")[:8]
    }