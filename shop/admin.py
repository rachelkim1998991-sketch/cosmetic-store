from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
# ProductImage va Banner modellarini importga qo'shdik
from .models import Brand, Category, Product, Favorite, CartItem, Sale, Order, OrderItem, ProductImage, Banner, User

@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)


# 1. Rasmlar galereyasi uchun inline klass yaratamiz
class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 3  # Avtomatik ravishda 3 ta bo'sh joy chiqaradi (istalgancha rasm qo'shish mumkin)
    fields = ('image', 'order')


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    inlines = [ProductImageInline]
    list_display = ('name', 'brand', 'category', 'price', 'cost_price', 'discount_price', 'stock', 'expiry_date',
                    'is_on_discount')
    list_filter = ('brand', 'category')
    search_fields = ('name', 'brand__name', 'skin_concern')
    list_editable = ('stock', 'discount_price')
    ordering = ('-created_at',)

    # 2. Ushbu qator orqali mahsulot sahifasiga rasmlar galereyasini ulaymiz
    inlines = [ProductImageInline]

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
    list_display = ('user', 'product', 'added_at')


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ('user', 'product', 'quantity', 'added_at')


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'phone_number', 'email', 'phone_verified', 'preferred_language', 'is_staff')
    fieldsets = UserAdmin.fieldsets + (
        ('Qo\'shimcha ma\'lumot', {'fields': ('phone_number', 'phone_verified', 'preferred_language')}),
    )


@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ('product', 'quantity', 'sold_price', 'sale_date', 'total_revenue', 'total_profit')
    list_filter = ('sale_date', 'product__brand', 'product__category')
    search_fields = ('product__name',)
    date_hierarchy = 'sale_date'
    ordering = ('-sale_date',)


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 1
    fields = ('product', 'quantity', 'unit_price')
    autocomplete_fields = ['product']


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    inlines = [OrderItemInline]
    list_display = ('id', 'customer_display', 'items_summary', 'discount_amount',
                    'total_amount', 'payment_method', 'status', 'created_at')
    list_filter = ('status', 'payment_method', 'created_at')
    search_fields = ('user__username', 'customer_name', 'customer_phone',
                     'telegram_username', 'transaction_id')
    readonly_fields = ('total_amount', 'transaction_id', 'provider_transaction_id',
                       'created_at', 'paid_at', 'stock_deducted')
    ordering = ('-created_at',)

    fieldsets = (
        ('Mijoz', {
            'fields': ('user', 'customer_name', 'customer_phone',
                       'telegram_user_id', 'telegram_username')
        }),
        ('To\'lov', {
            'fields': ('payment_method', 'status', 'discount_amount', 'total_amount'),
            'description': "Mahsulotlarni pastdagi jadvalga kiriting. Jami summa saqlagandan keyin avtomatik hisoblanadi. Chegirma ixtiyoriy (so'mda)."
        }),
        ('Texnik', {
            'classes': ('collapse',),
            'fields': ('transaction_id', 'provider_transaction_id',
                       'created_at', 'paid_at', 'stock_deducted')
        }),
    )

    def customer_display(self, obj):
        if obj.user:
            return obj.user.username
        return obj.customer_name or obj.telegram_username or '-'
    customer_display.short_description = 'Mijoz'

    def items_summary(self, obj):
        return ", ".join(f"{i.product.name} x{i.quantity}" for i in obj.items.all() if i.product)
    items_summary.short_description = 'Mahsulotlar'

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        order = form.instance
        order.recalculate_total()
        order.refresh_from_db()
        order.finalize_payment()


@admin.register(Banner)
class BannerAdmin(admin.ModelAdmin):
    list_display = ('title', 'link_product', 'order', 'is_active')
    list_editable = ('order', 'is_active')
