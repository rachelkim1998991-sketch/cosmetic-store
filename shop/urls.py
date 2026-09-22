from django.urls import path
from . import views

app_name='shop'

urlpatterns=[
    path('',views.home,name='home'),
    path('products/',views.product_list,name='product_list'),
    path('discount/',views.discount_list,name='discount_list'),
    path('favorite/',views.discount_list,name='discount_list'),
    path('favorite/<int:product_id>/',views.toggle_favorite,name='toggle_favorite'),
    path('cart/add/<int:product_id>/',views.add_to_cart,name='add_to_cart'),
    path('cart/remove/<int:item_id>/',views.remove_from_cart,name='remove_from_cart'),
    path('cart/',views.cart_view,name='cart'),
    path('favorites/',views.favorites_view,name='favorites'),
    path('ai-assistant/',views.ai_assistant,name='ai_assistant'),

]