import csv
import os
import re
from decimal import Decimal, InvalidOperation
from urllib.parse import urlparse

import requests
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction

from products.models import Category, Product, ProductVariant, ProductVariantImage


def clean_bool(value) -> bool:
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "y", "так", "да"}


def clean_text(value) -> str:
    if value is None:
        return ""
    return str(value).strip()


def clean_price(value):
    if value is None or value == "":
        return Decimal("0")
    text = str(value).strip().replace(",", ".")
    try:
        return Decimal(text)
    except InvalidOperation:
        return Decimal("0")


def filename_from_url(url: str, fallback: str = "image.jpg") -> str:
    parsed = urlparse(url)
    name = os.path.basename(parsed.path)
    if not name:
        return fallback
    return name


def safe_filename(name: str) -> str:
    return re.sub(r"[^a-zA-Z0-9._-]+", "_", name)


class Command(BaseCommand):
    help = "Импорт товаров, вариантов и фото из CSV UTF-8"

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            type=str,
            default="import_products.csv",
            help="Путь к CSV-файлу"
        )

    def handle(self, *args, **options):
        file_path = options["file"]

        if not os.path.exists(file_path):
            self.stdout.write(self.style.ERROR(f"Файл не найден: {file_path}"))
            return

        required_columns = [
            "category",
            "product_name",
            "description",
            "color",
            "size",
            "sku",
            "price",
            "stock_status",
            "is_new",
        ]

        created_products = 0
        created_variants = 0
        created_images = 0

        with open(file_path, "r", encoding="utf-8-sig", newline="") as f:
            sample = f.read(4096)
            f.seek(0)

            try:
                dialect = csv.Sniffer().sniff(sample, delimiters=",;")
            except csv.Error:
                dialect = csv.excel
                dialect.delimiter = ";"

            reader = csv.DictReader(f, dialect=dialect)

            if not reader.fieldnames:
                self.stdout.write(self.style.ERROR("CSV пустой или не читается заголовок"))
                return

            headers = [h.strip() for h in reader.fieldnames]
            self.stdout.write(f"Найденные колонки: {headers}")

            for column in required_columns:
                if column not in headers:
                    self.stdout.write(self.style.ERROR(f"Нет колонки: {column}"))
                    return

            image_columns = [h for h in headers if h.startswith("image_url_")]

            with transaction.atomic():
                for row_idx, row in enumerate(reader, start=2):
                    normalized_row = {
                        str(k).replace("\ufeff", "").strip(): v
                        for k, v in row.items()
                    }

                    category_name = clean_text(normalized_row.get("category"))
                    product_name = clean_text(normalized_row.get("product_name"))
                    description = clean_text(normalized_row.get("description"))
                    color = clean_text(normalized_row.get("color"))
                    size = clean_text(normalized_row.get("size"))
                    sku = clean_text(normalized_row.get("sku"))
                    price = clean_price(normalized_row.get("price"))
                    stock_status = clean_text(normalized_row.get("stock_status")) or "in_stock"
                    is_new = clean_bool(normalized_row.get("is_new"))

                    self.stdout.write(f"Строка {row_idx} -> category={category_name!r}, product_name={product_name!r}")

                    if not category_name or not product_name:
                        self.stdout.write(self.style.WARNING(
                            f"Строка {row_idx}: пропущена, нет category/product_name"
                        ))
                        continue

                    category_slug = category_name.lower().replace(" ", "-")
                    category, _ = Category.objects.get_or_create(
                        name=category_name,
                        defaults={
                            "slug": category_slug,
                            "is_active": True,
                        }
                    )

                    product, product_created = Product.objects.get_or_create(
                        category=category,
                        name=product_name,
                        defaults={
                            "price": price,
                            "description": description,
                            "is_new": is_new,
                            "stock_status": stock_status,
                        }
                    )

                    if product_created:
                        created_products += 1
                    else:
                        product.description = description or product.description
                        product.is_new = is_new
                        product.stock_status = stock_status or product.stock_status
                        if not product.price or product.price == 0:
                            product.price = price
                        product.save()

                    variant, variant_created = ProductVariant.objects.get_or_create(
                        product=product,
                        color_name=color,
                        size_name=size,
                        sku=sku,
                        defaults={
                            "price": price,
                            "stock_status": stock_status,
                            "is_active": True,
                        }
                    )

                    if variant_created:
                        created_variants += 1
                    else:
                        variant.price = price
                        variant.stock_status = stock_status
                        variant.is_active = True
                        variant.save()

                    for i, image_col in enumerate(image_columns, start=1):
                        image_url = clean_text(normalized_row.get(image_col))
                        if not image_url:
                            continue

                        try:
                            response = requests.get(image_url, timeout=20)
                            response.raise_for_status()
                        except Exception as e:
                            self.stdout.write(self.style.WARNING(
                                f"Строка {row_idx}: не удалось скачать фото {image_url} ({e})"
                            ))
                            continue

                        original_name = filename_from_url(
                            image_url,
                            fallback=f"image_{row_idx}_{i}.jpg"
                        )
                        final_name = safe_filename(
                            f"{product_name}_{color}_{size}_{i}_{original_name}"
                        )

                        image_obj = ProductVariantImage(
                            variant=variant,
                            is_main=(i == 1),
                            color_label=color,
                        )
                        image_obj.image.save(
                            final_name,
                            ContentFile(response.content),
                            save=True
                        )
                        created_images += 1

                    self.stdout.write(self.style.SUCCESS(
                        f"Строка {row_idx}: OK | {product_name} | {color or '-'} | {size or '-'}"
                    ))

        self.stdout.write(self.style.SUCCESS("Импорт завершён"))
        self.stdout.write(self.style.SUCCESS(f"Создано товаров: {created_products}"))
        self.stdout.write(self.style.SUCCESS(f"Создано вариантов: {created_variants}"))
        self.stdout.write(self.style.SUCCESS(f"Создано фото: {created_images}"))