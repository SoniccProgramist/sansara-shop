from django.db import transaction
from django.shortcuts import render, redirect, get_object_or_404

from products.models import Product, Category, Review, ProductVariant
from .models import Order, OrderItem
from .utils import send_telegram_message


def home(request):
    categories = Category.objects.filter(is_active=True)
    products = Product.objects.filter(category__is_active=True)

    q = (request.GET.get("q") or "").strip()
    if q:
        products = products.filter(name__icontains=q)

    products = products.prefetch_related(
        "images",
        "variants",
        "variants__images",
    )

    current_category = None
    new_products = Product.objects.filter(
        is_new=True,
        category__is_active=True
    ).prefetch_related("images", "variants", "variants__images")[:6]

    context = {
        "categories": categories,
        "products": products,
        "current_category": current_category,
        "new_products": new_products,
    }
    return render(request, "shop/home.html", context)


def product_list(request, category_slug=None):
    categories = Category.objects.filter(is_active=True)
    products = Product.objects.filter(
        category__is_active=True
    ).prefetch_related(
        "images",
        "variants",
        "variants__images",
    )

    current_category = None

    if category_slug:
        current_category = get_object_or_404(
            Category,
            slug=category_slug,
            is_active=True
        )
        products = products.filter(category=current_category)

    q = (request.GET.get("q") or "").strip()
    if q:
        products = products.filter(name__icontains=q)

    context = {
        "categories": categories,
        "products": products,
        "current_category": current_category,
    }
    return render(request, "shop/product_list.html", context)


def product_detail(request, pk):
    product = get_object_or_404(
        Product.objects.prefetch_related(
            "images",
            "variants",
            "variants__images",
        ),
        pk=pk
    )

    variants = list(product.variants.filter(is_active=True))

    colors = []
    sizes = []

    for variant in variants:
        if variant.color_name and variant.color_name not in colors:
            colors.append(variant.color_name)
        if variant.size_name and variant.size_name not in sizes:
            sizes.append(variant.size_name)

    selected_variant = variants[0] if variants else None

    if selected_variant and selected_variant.images.exists():
        gallery_images = selected_variant.images.all()
    else:
        gallery_images = product.images.all()

    variant_data = []
    for variant in variants:
        images = [
            {
                "url": image.image.url,
                "is_main": image.is_main,
                "color_label": image.color_label,
            }
            for image in variant.images.all()
        ]

        variant_data.append({
            "id": variant.id,
            "color_name": variant.color_name or "",
            "size_name": variant.size_name or "",
            "display_name": variant.display_name,
            "price": str(variant.price),
            "stock_status": variant.stock_status,
            "stock_label": variant.get_stock_status_display(),
            "images": images,
        })

    context = {
        "product": product,
        "variants": variants,
        "colors": colors,
        "sizes": sizes,
        "selected_variant": selected_variant,
        "gallery_images": gallery_images,
        "variant_data": variant_data,
    }
    return render(request, "shop/product_detail.html", context)


def add_to_cart(request, product_id):
    cart = request.session.get("cart", {})

    product_id = str(product_id)
    variant_id = request.POST.get("variant_id")

    cart_key = product_id
    if variant_id:
        cart_key = f"{product_id}:{variant_id}"

    cart[cart_key] = cart.get(cart_key, 0) + 1

    request.session["cart"] = cart
    request.session.modified = True
    return redirect("shop:cart_detail")


def cart_detail(request):
    cart = request.session.get("cart", {})

    product_ids = []
    variant_ids = []

    for key in cart.keys():
        parts = key.split(":")
        product_ids.append(parts[0])
        if len(parts) > 1:
            variant_ids.append(parts[1])

    products = Product.objects.filter(id__in=product_ids).prefetch_related(
        "images",
        "variants",
        "variants__images",
    )
    product_map = {str(product.id): product for product in products}

    variants = ProductVariant.objects.filter(id__in=variant_ids).prefetch_related("images")
    variant_map = {str(variant.id): variant for variant in variants}

    cart_items = []
    total_price = 0

    for key, quantity in cart.items():
        if quantity <= 0:
            continue

        parts = key.split(":")
        product_id = parts[0]
        variant_id = parts[1] if len(parts) > 1 else None

        product = product_map.get(product_id)
        if not product:
            continue

        variant = variant_map.get(variant_id) if variant_id else None

        if variant:
            price = variant.price
            variant_name = variant.display_name
            img = (
                variant.images.filter(is_main=True).first()
                or variant.images.first()
                or product.images.filter(is_main=True).first()
                or product.images.first()
            )
        else:
            price = product.price
            variant_name = ""
            img = product.images.filter(is_main=True).first() or product.images.first()

        image_url = img.image.url if img and img.image else None

        item_total = price * quantity
        total_price += item_total

        cart_items.append({
            "cart_key": key,
            "product": product,
            "variant": variant,
            "variant_name": variant_name,
            "price": price,
            "quantity": quantity,
            "item_total": item_total,
            "image_url": image_url,
        })

    error = None

    if request.method == "POST" and request.POST.get("action") == "checkout":
        phone = (request.POST.get("phone") or "").strip()
        full_name = (request.POST.get("full_name") or "").strip()
        city = (request.POST.get("city") or "").strip()

        if not cart_items:
            error = "Кошик порожній."
        elif not phone:
            error = "Вкажіть номер телефону."
        else:
            with transaction.atomic():
                order = Order.objects.create(
                    phone=phone,
                    total_price=total_price,
                    full_name=full_name,
                    city=city,
                )

                for item in cart_items:
                    OrderItem.objects.create(
                        order=order,
                        product=item["product"],
                        price=item["price"],
                        quantity=item["quantity"],
                    )

            items_text = "\n".join(
                [
                    f"• {item['product'].name}"
                    f"{' (' + item['variant_name'] + ')' if item['variant_name'] else ''}"
                    f" × {item['quantity']} = {item['item_total']} грн"
                    for item in cart_items
                ]
            )

            message = (
                f"🆕 Нове замовлення #{order.id}\n\n"
                f"👤 {full_name}\n"
                f"🏙️ {city}\n"
                f"📞 {phone}\n\n"
                f"Товари:\n{items_text}\n\n"
                f"💰 Сума: {total_price} грн"
            )

            send_telegram_message(message)

            request.session["cart"] = {}
            request.session.modified = True

            return redirect("shop:order_success", order_id=order.id)

    context = {
        "cart_items": cart_items,
        "total_price": total_price,
        "error": error,
    }
    return render(request, "shop/cart_detail.html", context)


def update_cart(request, product_id):
    if request.method != "POST":
        return redirect("shop:cart_detail")

    cart = request.session.get("cart", {})
    variant_id = request.POST.get("variant_id")

    try:
        quantity = int(request.POST.get("quantity", 1))
    except (TypeError, ValueError):
        quantity = 1

    cart_key = str(product_id)
    if variant_id:
        cart_key = f"{product_id}:{variant_id}"

    if quantity > 0:
        cart[cart_key] = quantity
    else:
        cart.pop(cart_key, None)

    request.session["cart"] = cart
    request.session.modified = True
    return redirect("shop:cart_detail")


def remove_from_cart(request, product_id):
    cart = request.session.get("cart", {})
    variant_id = request.GET.get("variant_id")

    cart_key = str(product_id)
    if variant_id:
        cart_key = f"{product_id}:{variant_id}"

    cart.pop(cart_key, None)

    request.session["cart"] = cart
    request.session.modified = True
    return redirect("shop:cart_detail")


def order_success(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    return render(request, "shop/order_success.html", {"order": order})


def reviews(request):
    success = False
    error = None

    if request.method == "POST":
        name = (request.POST.get("name") or "").strip()
        phone = (request.POST.get("phone") or "").strip()
        text = (request.POST.get("text") or "").strip()

        if not name or not phone or not text:
            error = "Будь ласка, заповніть усі поля."
        else:
            Review.objects.create(
                name=name,
                phone=phone,
                text=text,
                is_approved=False,
            )
            success = True

    approved_reviews = Review.objects.filter(is_approved=True)

    context = {
        "reviews": approved_reviews,
        "success": success,
        "error": error,
    }
    return render(request, "shop/reviews.html", context)


def about(request):
    return render(request, "shop/about.html")


def delivery(request):
    return render(request, "shop/delivery.html")
