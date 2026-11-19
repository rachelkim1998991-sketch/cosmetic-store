from django.urls import path
from . import views, api

app_name='shop'

urlpatterns=[
    path('',views.home,name='home'),
    path('products/',views.product_list,name='product_list'),
    path('discount/',views.discount_list,name='discount_list'),
    path('favorite/<int:product_id>/',views.toggle_favorite,name='toggle_favorite'),
    path('cart/add/<int:product_id>/',views.add_to_cart,name='add_to_cart'),
    path('cart/remove/<int:item_id>/',views.remove_from_cart,name='remove_from_cart'),
    path('cart/',views.cart_view,name='cart'),
    path('favorites/',views.favorites_view,name='favorites'),
    path('ai-assistant/',views.ai_assistant,name='ai_assistant'),
    path('product/<int:product_id>/', views.product_detail, name='product_detail'),
    path('stock-statistics/', views.stock_statistics, name='stock_statistics'),
    path('checkout/<int:product_id>/', views.checkout, name='checkout'),
    path('checkout/click-pay/<int:order_id>/', views.click_pay, name='click_pay'),
    path('checkout/payme-pay/<int:order_id>/', views.payme_pay, name='payme_pay'),
    path('payments/click/callback/', views.click_callback, name='click_callback'),
    path('payments/payme/callback/', views.payme_callback, name='payme_callback'),
    path('checkout/success/', views.checkout_success, name='checkout_success'),
    path('search-suggestions/', views.search_suggestions, name='search_suggestions'),

    # Telegram bot API
    path('api/categories/', api.categories, name='api_categories'),
    path('api/products/', api.products, name='api_products'),
    path('api/products/<int:product_id>/', api.product_detail, name='api_product_detail'),
    path('api/stats/', api.stats, name='api_stats'),
    path('api/ai/', api.ai_advice, name='api_ai'),
    path('api/orders/create/', api.order_create, name='api_order_create'),
    path('api/orders/<int:order_id>/', api.order_status, name='api_order_status'),

]