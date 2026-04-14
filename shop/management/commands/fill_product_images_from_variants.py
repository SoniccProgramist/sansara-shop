from django.core.management.base import BaseCommand
from django.db import transaction

from products.models import Product, ProductImage, ProductVariantImage


class Command(BaseCommand):
    help = "Заполняет ProductImage для товаров, у которых нет фото, используя фото вариаций"

    def handle(self, *args, **options):
        updated = 0
        skipped = 0

        products = Product.objects.prefetch_related(
            "images",
            "variants",
            "variants__images",
        )

        with transaction.atomic():
            for product in products:
                if product.images.exists():
                    skipped += 1
                    self.stdout.write(f"Пропуск: {product.name} — у товара уже есть фото")
                    continue

                variant_image = (
                    ProductVariantImage.objects
                    .filter(variant__product=product, is_main=True)
                    .select_related("variant", "variant__product")
                    .first()
                )

                if not variant_image:
                    variant_image = (
                        ProductVariantImage.objects
                        .filter(variant__product=product)
                        .select_related("variant", "variant__product")
                        .first()
                    )

                if not variant_image:
                    skipped += 1
                    self.stdout.write(f"Пропуск: {product.name} — у вариаций тоже нет фото")
                    continue

                ProductImage.objects.create(
                    product=product,
                    image=variant_image.image.name,
                    is_main=True,
                )

                updated += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Добавлено фото товару: {product.name} <- {variant_image.variant}"
                    )
                )

        self.stdout.write(self.style.SUCCESS(f"Готово. Обновлено товаров: {updated}"))
        self.stdout.write(self.style.WARNING(f"Пропущено: {skipped}"))