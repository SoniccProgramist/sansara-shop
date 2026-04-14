from django.urls import path
from .views import (
    product_list,
    product_detail,
    add_to_cart,
    cart_detail,
    remove_from_cart,
    update_cart,
    about,
    delivery,
    reviews,
    order_success,
    home,
)

app_name = "shop"

urlpatterns = [
    path("", home, name="home"),

    path("catalog/", product_list, name="product_list"),
    path("category/<slug:category_slug>/", product_list, name="category_filter"),
    path("product/<int:pk>/", product_detail, name="product_detail"),

    path("cart/", cart_detail, name="cart_detail"),
    path("cart/add/<int:product_id>/", add_to_cart, name="add_to_cart"),
    path("cart/update/<int:product_id>/", update_cart, name="update_cart"),
    path("cart/remove/<int:product_id>/", remove_from_cart, name="remove_from_cart"),

    path("order/success/<int:order_id>/", order_success, name="order_success"),

    path("pro-nas/", about, name="about"),
    path("dostavka/", delivery, name="delivery"),
    path("reviews/", reviews, name="reviews"),
]