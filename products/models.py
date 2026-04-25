from django.db import models


class Category(models.Model):
    name = models.CharField(max_length=100, verbose_name='Название')
    slug = models.SlugField(max_length=120, unique=True, verbose_name='URL')
    is_active = models.BooleanField(default=True, verbose_name='Активна')
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='children',
        verbose_name='Батьківська категорія'
    )
    class Meta:
        verbose_name = 'Категория'
        verbose_name_plural = 'Категории'

    def __str__(self):
        if self.parent:
            return f"{self.parent.name} → {self.name}"
        return self.name

    def get_descendants_ids(self):
        ids = [self.id]
        for child in self.children.filter(is_active=True):
            ids.extend(child.get_descendants_ids())
        return ids


class Product(models.Model):
    STOCK_CHOICES = [
        ("in_stock", "В наявності"),
        ("on_order", "Під замовлення"),
        ("out_of_stock", "Немає в наявності"),
    ]

    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name='products'
    )
    name = models.CharField(max_length=200)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField(blank=True)
    is_new = models.BooleanField(default=False, verbose_name="Новинка")
    stock_status = models.CharField(
        max_length=20,
        choices=STOCK_CHOICES,
        default="in_stock",
        verbose_name="Наявність"
    )

    def __str__(self):
        return self.name

    @property
    def has_variants(self):
        return self.variants.exists()

    @property
    def base_price(self):
        first_variant = self.variants.filter(is_active=True).order_by("price").first()
        return first_variant.price if first_variant else self.price

    @property
    def base_stock_status(self):
        first_variant = self.variants.filter(is_active=True).first()
        return first_variant.stock_status if first_variant else self.stock_status


class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='products/')
    is_main = models.BooleanField(default=False)

    def __str__(self):
        return f"Image for {self.product_id}"


class ProductVariant(models.Model):
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="variants",
        verbose_name="Товар"
    )
    color_name = models.CharField(max_length=100, blank=True, verbose_name="Колір")
    size_name = models.CharField(max_length=100, blank=True, verbose_name="Розмір")
    sku = models.CharField(max_length=100, blank=True, verbose_name="Артикул")
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Ціна")
    stock_status = models.CharField(
        max_length=20,
        choices=Product.STOCK_CHOICES,
        default="in_stock",
        verbose_name="Наявність"
    )
    is_active = models.BooleanField(default=True, verbose_name="Активний")

    class Meta:
        verbose_name = "Варіант товару"
        verbose_name_plural = "Варіанти товарів"
        ordering = ["product", "color_name", "size_name"]

    def __str__(self):
        parts = [self.product.name]
        if self.color_name:
            parts.append(self.color_name)
        if self.size_name:
            parts.append(self.size_name)
        return " / ".join(parts)

    @property
    def display_name(self):
        parts = []
        if self.color_name:
            parts.append(self.color_name)
        if self.size_name:
            parts.append(self.size_name)
        return " / ".join(parts) if parts else self.product.name


class ProductVariantImage(models.Model):
    variant = models.ForeignKey(
        ProductVariant,
        on_delete=models.CASCADE,
        related_name="images",
        verbose_name="Варіант"
    )
    image = models.ImageField(upload_to="products/")
    is_main = models.BooleanField(default=False, verbose_name="Головне фото")
    color_label = models.CharField(max_length=100, blank=True, verbose_name="Підпис кольору")

    class Meta:
        verbose_name = "Фото варіанту"
        verbose_name_plural = "Фото варіантів"

    def __str__(self):
        return f"Фото для {self.variant}"


class Review(models.Model):
    name = models.CharField("Ім’я", max_length=80)
    phone = models.CharField("Телефон", max_length=30)
    text = models.TextField("Відгук", max_length=2000)

    is_approved = models.BooleanField("Показувати на сайті", default=False)
    created_at = models.DateTimeField("Створено", auto_now_add=True)

    class Meta:
        verbose_name = "Відгук"
        verbose_name_plural = "Відгуки"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} ({self.phone})"