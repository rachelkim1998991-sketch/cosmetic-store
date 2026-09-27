from django.contrib.auth.models import AbstractUser
from django.db import models
from django.conf import settings

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
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='orders')
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True)
    quantity = models.PositiveIntegerField(default=1)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Jami summa (so'm)")

    payment_method = models.CharField(max_length=10, choices=PAYMENT_CHOICES)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')

    transaction_id = models.CharField(max_length=100, blank=True, null=True, unique=True)
    provider_transaction_id = models.CharField(max_length=100, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return f"Buyurtma #{self.id} - {self.user} - {self.total_amount} so'm ({self.get_status_display()})"


