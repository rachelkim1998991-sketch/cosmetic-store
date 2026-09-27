from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Brand,Category,Product,Favorite,CartItem,User,Sale

@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display=('name',)
    search_fields=('name',)

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display=('name','brand','category','price','cost_price','discount_price','stock','expiry_date','is_on_discount')
    list_filter=('brand','category')
    search_fields=('name','brand__name','skin_concern')
    list_editable=('stock','discount_price')
    ordering=('-created_at',)

    fieldsets = (
        ('Asosiy ma\'lumot', {
            'fields': ('name', 'brand', 'category', 'description', 'image')
        }),
        ('Narx va chegirma', {
            'fields': ('price', 'cost_price', 'discount_price')
        }),
        ('Ombor', {
            'fields': ('stock', 'expiry_date')
        }),
        ('AI tavsiyasi uchun', {
            'fields': ('skin_concern',)
        }),
    )

@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display=('user','product','added_at')

@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display=('user','product','quantity','added_at')

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display=('username','phone_number','email','phone_verified','preferred_language','is_staff')
    fieldsets=UserAdmin.fieldsets+(
    ('Qo\'shimcha ma\'lumot',{'fields':('phone_number','phone_verified','preferred_language')}),
    )

@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ('product', 'quantity', 'sold_price', 'sale_date', 'total_revenue', 'total_profit')
    list_filter = ('sale_date', 'product__brand', 'product__category')
    search_fields = ('product__name',)
    date_hierarchy = 'sale_date'
    ordering = ('-sale_date',)
