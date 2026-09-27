import os
import json
from google import genai

from django.shortcuts import render,redirect,get_object_or_404
from django.db.models import Q, Sum, Count
from .models import Product, Category, Brand, Favorite, CartItem, Sale,Order
from datetime import timedelta
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from django.contrib.auth.decorators import user_passes_test
from django.http import JsonResponse,HttpResponse
from django.views.decorators.http import require_POST
from django.conf import settings
from decimal import Decimal
from django.views.decorators.csrf import csrf_exempt
import hashlib
import time
import base64
import json as json_lib

def home(request):
    products=Product.objects.all()[:12]
    categories=Category.objects.all()

    user_favorite_ids=[]
    if request.user.is_authenticated:
        user_favorite_ids=list(
            Favorite.objects.filter(user=request.user).values_list('product_id',flat=True)
        )
    context={
        'products':products,
        'categories':categories,
        'user_favorite_ids':user_favorite_ids,
    }
    return render(request,'shop/home.html',context)

def product_list(request):
    products=Product.objects.all()
    categories=Category.objects.all()
    brands=Brand.objects.all()

    view_mode=request.GET.get('view','all')

    category_id=request.GET.get('category')
    if category_id:
        products=products.filter(category_id=category_id)

    brand_id=request.GET.get('brand')
    if brand_id:
        products=products.filter(brand_id=brand_id)

    query=request.GET.get('q')
    if query:
        products=products.filter(
            Q(name__icontains=query) |
            Q(brand__name__icontains=query)|
            Q(category__name__icontains=query)
        )

    user_favorite_ids=[]
    if request.user.is_authenticated:
        user_favorite_ids=list(
            Favorite.objects.filter(user=request.user).values_list('product_id',flat=True)
        )

    context={
        'products':products,
        'categories':categories,
        'brands':brands,
        'selected_category':category_id,
        'selected_brand':brand_id,
        'query':query or '',
        'view_mode':view_mode,
        'user_favorite_ids':user_favorite_ids,
    }

    return render(request,'shop/product_list.html',context)

def discount_list(request):
    products=Product.objects.filter(discount_price__isnull=False)
    categories=Category.objects.all()
    brands=Brand.objects.all()
    context={
        'products':products,
        'categories':categories,
        'brands':brands,
        'page_title':'Chegirmachi tovarlar',
    }
    return render(request,'shop/product_list.html',context)


@login_required
@require_POST
def toggle_favorite(request,product_id):
    product=Product.objects.get(id=product_id)
    favorite,created=Favorite.objects.get_or_create(user=request.user,product=product)

    if not created:
        favorite.delete()
        return JsonResponse({'status':'removed'})

    return JsonResponse({'status':'added'})

@login_required
@require_POST
def add_to_cart(request,product_id):
    product=Product.objects.get(id=product_id)
    cart_item,created=CartItem.objects.get_or_create(user=request.user,product=product)

    if not created:
        cart_item.quantity+=1
        cart_item.save()

    return JsonResponse({'status':'added','quantity':cart_item.quantity})

@login_required
def cart_view(request):
    cart_items=CartItem.objects.filter(user=request.user).select_related('product')
    total=sum(item.product.final_price * item.quantity for item in cart_items)
    context={
        'cart_items':cart_items,
        'total':total,
    }
    return render(request,'shop/cart.html',context)

@login_required
def favorites_view(request):
    favorites=Favorite.objects.filter(user=request.user).select_related('product')
    context={
        'favorites':favorites,
    }
    return render(request,'shop/favorites.html',context)

@login_required
@require_POST
def remove_from_cart(request,item_id):
    CartItem.objects.filter(id=item_id,user=request.user).delete()
    return JsonResponse({'status':'removed'})

@login_required
@require_POST
def ai_assistant(request):
    try:
        data = json.loads(request.body)
        user_message = data.get('message', '').strip()
        history = data.get('history', [])
    except (json.JSONDecodeError, AttributeError):
        return JsonResponse({'error': 'Noto\'g\'ri so\'rov'}, status=400)

    if not user_message:
        return JsonResponse({'error': 'Xabar bo\'sh bo\'lmasligi kerak'}, status=400)

    products = Product.objects.select_related('brand', 'category').all()

    if not products.exists():
        return JsonResponse({'reply': 'Hozircha bazada mahsulotlar mavjud emas.'})

    catalog_lines = []
    for p in products:
        concern_text = p.skin_concern or "ko'rsatilmagan"
        line = f"- ID:{p.id} | {p.name} | Brend: {p.brand.name} | Turi: {p.category.name} | Narxi: {p.final_price} so'm | Muammo: {concern_text}"
        catalog_lines.append(line)
    catalog_text = "\n".join(catalog_lines)

    system_prompt = f"""Sen "Cosmetic Store" internet do'konining AI yordamchisisan.
Sening vazifang — mijozning tashvishiga (terisi, sochi, muammosi) qarab, FAQAT quyidagi ro'yxatdagi mahsulotlardan mos kelganini tavsiya qilish.

MUHIM QOIDA — ANIQLASHTIRISH:
Agar mijozning so'rovi umumiy yoki noaniq bo'lsa (masalan faqat "terim quruq" deb yozsa, boshqa tafsilot bermasa), DARHOL mahsulot tavsiya qilma. Buning o'rniga 1-2 ta aniqlashtiruvchi savol ber, masalan:
- Sizga bitta mahsulot kerakmi (masalan faqat krem), yoki to'liq parvarish to'plami (tozalovchi + toner + krem) kerakmi?
- Terangizda boshqa muammolar ham bormi (masalan aknalar, qizarish, keksarish belgilari)?
- Byudjetingiz taxminan qancha?

Mijoz javob berganidan keyin, shu ma'lumotlarga asoslanib, ro'yxatdan mos mahsulot(lar)ni tavsiya qil.

Agar mijoz so'rovi allaqachon aniq bo'lsa (masalan "menga faqat toner kerak, terim yog'li" desa), to'g'ridan-to'g'ri tavsiya berishing mumkin, savol berishning hojati yo'q.

BOSHQA QOIDALAR:
1. Faqat ro'yxatdagi mahsulotlardan tanla, o'zingdan mahsulot o'ylab topma.
2. Agar ro'yxatda mos mahsulot bo'lmasa, buni ochiq ayt.
3. Javobni o'zbek tilida, qisqa va samimiy uslubda yoz.
4. Tavsiya qilganda mahsulot nomini, brendini va narxini ayt, nima uchun mos kelishini tushuntir.
5. Bir nechta mahsulot tavsiya qilishing mumkin.
6. FORMATLASH: agar javobingda bir nechta ma'lumot bandi bo'lsa (masalan mahsulot nomi, narxi, brendi, yoki buyurtma tafsilotlari), HAR BIR BANDNI ALOHIDA QATORGA yoz. Bir qatorga bir nechta bandni bitta chiziqcha bilan ajratib yozma. Muhim so'zlarni **qalin** qilib belgila

MAHSULOTLAR RO'YXATI:
{catalog_text}
"""

    # Suhbat tarixini matn shakliga o'giramiz
    conversation_text = ""
    for msg in history:
        role = "Mijoz" if msg.get('role') == 'user' else "Yordamchi"
        conversation_text += f"{role}: {msg.get('text', '')}\n"

    full_prompt = f"{system_prompt}\n\nSUHBAT TARIXI:\n{conversation_text}\nMijoz: {user_message}\nYordamchi:"

    try:
        client = genai.Client(api_key=os.getenv('GEMINI_API_KEY'))
        response = client.models.generate_content(
            model='gemini-3.6-flash',
            contents=full_prompt
        )
        ai_reply = response.text
    except Exception as e:
        error_text = str(e)
        if 'UNAVAILABLE' in error_text or '503' in error_text:
            return JsonResponse({'reply': 'Hozir AI xizmati band, biroz kutib qayta urinib ko\'ring. 🙏'})
        if 'RESOURCE_EXHAUSTED' in error_text or '429' in error_text:
            return JsonResponse(
                {'reply': 'Bugungi so\'rovlar chegarasiga yetdik, biroz kuting va qayta urinib ko\'ring. 🙏'})
        return JsonResponse({'error': f'AI xizmatida xatolik: {error_text}'}, status=500)
    return JsonResponse({'reply': ai_reply})


def product_detail(request, product_id):
    product = Product.objects.select_related('brand', 'category').get(id=product_id)

    user_favorite_ids = []
    if request.user.is_authenticated:
        user_favorite_ids = list(
            Favorite.objects.filter(user=request.user).values_list('product_id', flat=True)
        )

    context = {
        'product': product,
        'user_favorite_ids': user_favorite_ids,
    }
    return render(request, 'shop/product_detail.html', context)


@user_passes_test(lambda u: u.is_superuser)
def stock_statistics(request):
    products = Product.objects.select_related('brand', 'category').order_by('stock')

    total_products = products.count()
    total_stock_value = sum(p.final_price * p.stock for p in products)
    low_stock_products = products.filter(stock__lte=5)
    out_of_stock_products = products.filter(stock=0)

    category_stats = (
        Product.objects.values('category__name')
        .annotate(total_stock=Sum('stock'), item_count=Count('id'))
        .order_by('-total_stock')
    )

    period = request.GET.get('period', '30')
    today = timezone.now().date()

    if period == '7':
        start_date = today - timedelta(days=7)
    elif period == '30':
        start_date = today - timedelta(days=30)
    elif period == 'all':
        start_date = None
    else:
        start_date = today - timedelta(days=30)

    sales_qs = Sale.objects.select_related('product', 'product__brand')
    if start_date:
        sales_qs = sales_qs.filter(sale_date__gte=start_date)

    total_revenue = sum(s.total_revenue for s in sales_qs)
    total_profit = sum(s.total_profit for s in sales_qs)
    total_sold_quantity = sum(s.quantity for s in sales_qs)

    best_sellers = (
        sales_qs.values('product__id', 'product__name', 'product__brand__name')
        .annotate(total_qty=Sum('quantity'), total_rev=Sum('sold_price'))
        .order_by('-total_qty')[:10]
    )

    expiry_soon_date = today + timedelta(days=30)
    expiring_soon = products.filter(
        expiry_date__lte=expiry_soon_date,
        expiry_date__gte=today
    ).order_by('expiry_date')

    expired_products = products.filter(expiry_date__lt=today)

    context = {
        'products': products,
        'total_products': total_products,
        'total_stock_value': total_stock_value,
        'low_stock_products': low_stock_products,
        'low_stock_count': low_stock_products.count(),
        'out_of_stock_count': out_of_stock_products.count(),
        'category_stats': category_stats,
        'period': period,
        'total_revenue': total_revenue,
        'total_profit': total_profit,
        'total_sold_quantity': total_sold_quantity,
        'best_sellers': best_sellers,
        'expiring_soon': expiring_soon,
        'expired_products': expired_products,
    }
    return render(request, 'shop/stock_statistics.html', context)


@login_required
def checkout(request, product_id):
    product = Product.objects.get(id=product_id)

    if request.method == 'POST':
        payment_method = request.POST.get('payment_method')
        quantity = int(request.POST.get('quantity', 1))
        total_amount = product.final_price * quantity

        order = Order.objects.create(
            user=request.user,
            product=product,
            quantity=quantity,
            total_amount=total_amount,
            payment_method=payment_method,
            status='pending',
        )
        order.transaction_id = f"order-{order.id}-{int(time.time())}"
        order.save()

        if payment_method == 'click':
            return redirect('shop:click_pay', order_id=order.id)
        elif payment_method == 'payme':
            return redirect('shop:payme_pay', order_id=order.id)

    context = {'product': product}
    return render(request, 'shop/checkout.html', context)


@login_required
def click_pay(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)

    return_url = request.build_absolute_uri('/checkout/success/')
    click_url = (
        f"https://my.click.uz/services/pay"
        f"?service_id={settings.CLICK_SERVICE_ID}"
        f"&merchant_id={settings.CLICK_MERCHANT_ID}"
        f"&amount={order.total_amount}"
        f"&transaction_param={order.transaction_id}"
        f"&return_url={return_url}"
    )
    return redirect(click_url)


@csrf_exempt
def click_callback(request):
    data = request.POST

    click_trans_id = data.get('click_trans_id')
    service_id = data.get('service_id')
    merchant_trans_id = data.get('merchant_trans_id')
    amount = data.get('amount')
    action = data.get('action')
    sign_time = data.get('sign_time')
    sign_string = data.get('sign_string')
    error = data.get('error')

    try:
        order = Order.objects.get(transaction_id=merchant_trans_id, payment_method='click')
    except Order.DoesNotExist:
        return JsonResponse({'error': -5, 'error_note': 'Buyurtma topilmadi'})

    if action == '0':  # Prepare
        expected_sign = hashlib.md5(
            f"{click_trans_id}{service_id}{settings.CLICK_SECRET_KEY}{merchant_trans_id}{amount}{action}{sign_time}".encode()
        ).hexdigest()

        if sign_string != expected_sign:
            return JsonResponse({'error': -1, 'error_note': 'Imzo mos emas'})

        return JsonResponse({
            'click_trans_id': click_trans_id,
            'merchant_trans_id': merchant_trans_id,
            'merchant_prepare_id': order.id,
            'error': 0,
            'error_note': 'Success',
        })

    elif action == '1':  # Complete
        merchant_prepare_id = data.get('merchant_prepare_id')
        expected_sign = hashlib.md5(
            f"{click_trans_id}{service_id}{settings.CLICK_SECRET_KEY}{merchant_trans_id}{merchant_prepare_id}{amount}{action}{sign_time}".encode()
        ).hexdigest()

        if sign_string != expected_sign:
            return JsonResponse({'error': -1, 'error_note': 'Imzo mos emas'})

        if error and int(error) < 0:
            order.status = 'failed'
        else:
            order.status = 'paid'
            order.provider_transaction_id = click_trans_id
            order.paid_at = timezone.now()
        order.save()

        return JsonResponse({
            'click_trans_id': click_trans_id,
            'merchant_trans_id': merchant_trans_id,
            'merchant_confirm_id': order.id,
            'error': 0,
            'error_note': 'Success',
        })

    return JsonResponse({'error': -3, 'error_note': 'Noma\'lum amal'})



@login_required
def payme_pay(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)

    amount_tiyin = int(order.total_amount * 100)  # Payme summani tiyinda kutadi
    params = f"m={settings.PAYME_MERCHANT_ID};ac.order_id={order.id};a={amount_tiyin}"
    encoded_params = base64.b64encode(params.encode()).decode()

    payme_url = f"https://checkout.paycom.uz/{encoded_params}"
    return redirect(payme_url)


@csrf_exempt
def payme_callback(request):
    try:
        body = json_lib.loads(request.body)
    except (json_lib.JSONDecodeError, AttributeError):
        return JsonResponse({'error': {'code': -32700, 'message': 'Parse error'}})

    auth_header = request.META.get('HTTP_AUTHORIZATION', '')
    expected_auth = 'Basic ' + base64.b64encode(f"Paycom:{settings.PAYME_SECRET_KEY}".encode()).decode()

    if auth_header != expected_auth:
        return JsonResponse({'error': {'code': -32504, 'message': 'Ruxsat yo\'q'}})

    method = body.get('method')
    params = body.get('params', {})
    request_id = body.get('id')

    if method == 'CheckPerformTransaction':
        order_id = params.get('account', {}).get('order_id')
        try:
            order = Order.objects.get(id=order_id, payment_method='payme')
        except Order.DoesNotExist:
            return JsonResponse({'error': {'code': -31050, 'message': 'Buyurtma topilmadi'}, 'id': request_id})

        return JsonResponse({'result': {'allow': True}, 'id': request_id})

    elif method == 'CreateTransaction':
        order_id = params.get('account', {}).get('order_id')
        trans_id = params.get('id')
        try:
            order = Order.objects.get(id=order_id, payment_method='payme')
        except Order.DoesNotExist:
            return JsonResponse({'error': {'code': -31050, 'message': 'Buyurtma topilmadi'}, 'id': request_id})

        order.provider_transaction_id = trans_id
        order.save()

        return JsonResponse({
            'result': {
                'create_time': int(time.time() * 1000),
                'transaction': str(order.id),
                'state': 1,
            },
            'id': request_id,
        })

    elif method == 'PerformTransaction':
        trans_id = params.get('id')
        try:
            order = Order.objects.get(provider_transaction_id=trans_id)
        except Order.DoesNotExist:
            return JsonResponse({'error': {'code': -31003, 'message': 'Tranzaksiya topilmadi'}, 'id': request_id})

        order.status = 'paid'
        order.paid_at = timezone.now()
        order.save()

        return JsonResponse({
            'result': {
                'transaction': str(order.id),
                'perform_time': int(time.time() * 1000),
                'state': 2,
            },
            'id': request_id,
        })

    elif method == 'CancelTransaction':
        trans_id = params.get('id')
        try:
            order = Order.objects.get(provider_transaction_id=trans_id)
        except Order.DoesNotExist:
            return JsonResponse({'error': {'code': -31003, 'message': 'Tranzaksiya topilmadi'}, 'id': request_id})

        order.status = 'cancelled'
        order.save()

        return JsonResponse({
            'result': {
                'transaction': str(order.id),
                'cancel_time': int(time.time() * 1000),
                'state': -1,
            },
            'id': request_id,
        })

    elif method == 'CheckTransaction':
        trans_id = params.get('id')
        try:
            order = Order.objects.get(provider_transaction_id=trans_id)
        except Order.DoesNotExist:
            return JsonResponse({'error': {'code': -31003, 'message': 'Tranzaksiya topilmadi'}, 'id': request_id})

        state_map = {'pending': 1, 'paid': 2, 'cancelled': -1, 'failed': -2}
        return JsonResponse({
            'result': {
                'create_time': int(order.created_at.timestamp() * 1000),
                'perform_time': int(order.paid_at.timestamp() * 1000) if order.paid_at else 0,
                'cancel_time': 0,
                'transaction': str(order.id),
                'state': state_map.get(order.status, 1),
            },
            'id': request_id,
        })

    return JsonResponse({'error': {'code': -32601, 'message': 'Metod topilmadi'}, 'id': request_id})

@login_required
def checkout_success(request):
    return render(request, 'shop/checkout_success.html')