from django.db import models

class Order(models.Model):
    STATUS_CHOICES = [
        ("new", "Нове"),
        ("processing", "В обробці"),
        ("done", "Виконано"),
        ("canceled", "Скасовано"),
    ]

    full_name = models.CharField(max_length=120, verbose_name="Ім’я та прізвище", default="")
    city = models.CharField(max_length=80, verbose_name="Місто", default="")

    phone = models.CharField(max_length=32, verbose_name="Телефон")
    total_price = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Сума")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="new", verbose_name="Статус")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Створено")

    def __str__(self):
        return f"Замовлення #{self.id} ({self.phone})"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name="items", on_delete=models.CASCADE, verbose_name="Замовлення")
    product = models.ForeignKey("products.Product", on_delete=models.PROTECT, null=True, blank=True, verbose_name="Товар")
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Ціна")
    quantity = models.PositiveIntegerField(default=1, verbose_name="К-сть")

    def __str__(self):
        return f"{self.product} x{self.quantity}"

    def product_name(self):
        return self.product.name if self.product else ""

    product_name.short_description = "Товар"

    @property
    def line_total(self):
        return self.price * self.quantity

    @property
    def main_image(self):
        img = self.images.filter(is_main=True).first()
        return img or self.images.first()