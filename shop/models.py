from django.contrib.auth.models import AbstractUser
from django.db import models
from django.conf import settings
from django.utils import timezone

class Brand(models.Model):
    name=models.CharField(max_length=100,unique=True)
    logo=models.ImageField(upload_to='brands/',blank=True,null=True)

    def __str__(self):
        return self.name

class Category(models.Model):
    name=models.CharField(max_length=100)

    def __str__(self):
        return self.name

class Product(models.Model):
    name=models.CharField(max_length=200)
    brand=models.ForeignKey(Brand,on_delete=models.CASCADE,related_name='products')
    category=models.ForeignKey(Category,on_delete=models.CASCADE,related_name='products')
    description=models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    cost_price = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Tannarx")
    discount_price=models.DecimalField(max_digits=10,decimal_places=2,blank=True,null=True)

    stock=models.PositiveIntegerField(default=0)
    expiry_date=models.DateField(verbose_name='srok godnosti')

    image=models.ImageField(upload_to='products/',blank=True,null=True)

    skin_concern=models.CharField(
        max_length=255,blank=True,
        help_text="Masalan: quruq teri,akne,yog'li teri,ajinlar"
    )

    created_at=models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.brand.name}-{self.name}"

    @property
    def is_on_discount(self):
        return self.discount_price is not None and self.discount_price<self.price

    @property
    def final_price(self):
        return self.discount_price if self.is_on_discount else self.price


class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='gallery')
    image = models.ImageField(upload_to='products/gallery/')
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.product.name} - rasm {self.order}"

class Favorite(models.Model):
    user=models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    product=models.ForeignKey(Product,on_delete=models.CASCADE)
    added_at=models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together=('user','product')

class CartItem(models.Model):
    user=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE)
    product=models.ForeignKey(Product,on_delete=models.CASCADE)
    quantity=models.PositiveIntegerField(default=1)
    added_at=models.DateTimeField(auto_now_add=True)

class User(AbstractUser):
    phone_number=models.CharField(max_length=20)
    phone_verified=models.BooleanField(default=False)
    preferred_language=models.CharField(
        max_length=10,
        choices=[('uz',"O'zbekcha"),('ru','Русский'),('en',"English")],
        default='uz'
    )

    def __str__(self):
        return self.phone_number or self.username

class Sale(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='sales')
    quantity = models.PositiveIntegerField(default=1, verbose_name="Miqdor")
    sold_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Sotilgan narx")
    sale_date = models.DateField(verbose_name="Sotuv sanasi")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.product.name} - {self.quantity} dona ({self.sale_date})"

    @property
    def total_revenue(self):
        return self.sold_price * self.quantity

    @property
    def total_profit(self):
        return (self.sold_price - self.product.cost_price) * self.quantity


class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Kutilmoqda'),
        ('paid', 'To\'landi'),
        ('cancelled', 'Bekor qilindi'),
        ('failed', 'Muvaffaqiyatsiz'),
    ]

    PAYMENT_CHOICES = [
        ('click', 'Click'),
        ('payme', 'Payme'),
        ('cash', 'Naqd / joyida'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='orders', null=True,
                             blank=True)
    telegram_user_id = models.CharField(max_length=50, blank=True, null=True)
    telegram_username = models.CharField(max_length=100, blank=True, null=True)
    customer_name = models.CharField(max_length=150, blank=True, null=True)
    customer_phone = models.CharField(max_length=30, blank=True, null=True)

    discount_amount = models.DecimalField(
        max_digits=12, decimal_places=2, default=0, blank=True,
        verbose_name="Chegirma (so'm)"
    )
    total_amount = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        verbose_name="Jami summa (so'm)", editable=False
    )

    payment_method = models.CharField(max_length=10, choices=PAYMENT_CHOICES)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')

    transaction_id = models.CharField(max_length=100, blank=True, null=True, unique=True)
    provider_transaction_id = models.CharField(max_length=100, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(blank=True, null=True)
    stock_deducted = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

    def recalculate_total(self):
        subtotal = sum(item.subtotal for item in self.items.all())
        discount = self.discount_amount or 0
        total = subtotal - discount
        if total < 0:
            total = 0
        self.total_amount = total
        Order.objects.filter(pk=self.pk).update(total_amount=total)

    def finalize_payment(self):
        """Status 'paid' bo'lganda, har bir mahsulot uchun Sale yaratadi va stockni kamaytiradi."""
        if self.status != 'paid' or self.stock_deducted:
            return

        for item in self.items.select_related('product').all():
            if not item.product:
                continue
            Sale.objects.create(
                product=item.product,
                quantity=item.quantity,
                sold_price=item.unit_price,
                sale_date=timezone.now().date(),
            )
            item.product.stock = max(0, item.product.stock - item.quantity)
            item.product.save()

        self.stock_deducted = True
        self.paid_at = self.paid_at or timezone.now()
        Order.objects.filter(pk=self.pk).update(stock_deducted=True, paid_at=self.paid_at)

    def __str__(self):
        return f"Buyurtma #{self.id} - {self.user} - {self.total_amount} so'm ({self.get_status_display()})"

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, verbose_name="Birlik narxi")

    def save(self, *args, **kwargs):
        if not self.unit_price and self.product:
            self.unit_price = self.product.final_price
        super().save(*args, **kwargs)

    @property
    def subtotal(self):
        return (self.unit_price or 0) * self.quantity

    def __str__(self):
        return f"{self.product} x {self.quantity}"


class Banner(models.Model):
    title = models.CharField(max_length=200, blank=True)
    image = models.ImageField(upload_to='banners/')
    link_product = models.ForeignKey(Product, on_delete=models.SET_NULL, blank=True, null=True)
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return self.title or f"Banner {self.id}"




class SearchQuery(models.Model):
    """Telegram botdagi qidiruv tarixi (statistika uchun)."""
    user_id = models.BigIntegerField(null=True, blank=True)
    query_text = models.CharField(max_length=200)
    searched_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.query_text