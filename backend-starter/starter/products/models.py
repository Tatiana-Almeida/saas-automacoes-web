import os
from decimal import Decimal
from io import BytesIO

from django.core.files.base import ContentFile
from django.core.validators import MinValueValidator
from django.db import models
from django.utils.text import slugify
from PIL import Image


class Category(models.Model):
    name = models.CharField(max_length=120, unique=True)
    slug = models.SlugField(max_length=140, unique=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ("name",)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.name


class Tag(models.Model):
    name = models.CharField(max_length=80, unique=True)
    slug = models.SlugField(max_length=100, unique=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ("name",)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.name


class Product(models.Model):
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to="products/%Y/%m/", blank=True, null=True)
    image_thumb = models.ImageField(
        upload_to="products/thumbs/%Y/%m/", blank=True, null=True
    )
    price = models.DecimalField(
        max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0"))]
    )
    is_active = models.BooleanField(default=True)
    categories = models.ManyToManyField(Category, related_name="products", blank=True)
    tags = models.ManyToManyField(Tag, related_name="products", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("name",)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        # Save first to ensure image file is available in storage
        super().save(*args, **kwargs)
        # Generate thumbnail if needed
        if self.image and (not self.image_thumb or self._thumbnail_needs_update()):
            try:
                self._generate_thumbnail()
            except Exception:
                # skip thumbnail on errors
                pass

    def _thumbnail_needs_update(self):
        # Regenerate if thumb missing or base filename changed
        if not self.image_thumb:
            return True
        base = os.path.splitext(os.path.basename(self.image.name))[0]
        thumb_base = os.path.splitext(os.path.basename(self.image_thumb.name))[0]
        return not thumb_base.startswith(base)

    def _generate_thumbnail(self, size=(300, 300)):
        img = Image.open(self.image)
        img = img.convert("RGB")
        img.thumbnail(size, Image.LANCZOS)
        buffer = BytesIO()
        img.save(buffer, format="JPEG", quality=85)
        buffer.seek(0)
        base = os.path.splitext(os.path.basename(self.image.name))[0]
        filename = f"{base}_thumb.jpg"
        content = ContentFile(buffer.read())
        self.image_thumb.save(filename, content, save=False)
        super().save(update_fields=["image_thumb"])

    def __str__(self) -> str:
        return self.name
