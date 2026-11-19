"""Telegram bot uchun JSON API.

Har bir so'rovda `X-Bot-Token` headeri BOT_API_TOKEN ga teng bo'lishi shart.
"""
import hmac
import json
import time
from decimal import Decimal, InvalidOperation
from functools import wraps

from django.conf import settings
from django.db import transaction
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from .models import Category, Order, OrderItem, Product


def bot_auth(view):
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        expected = getattr(settings, 'BOT_API_TOKEN', '')
        token = request.headers.get('X-Bot-Token', '')
        if not expected or not hmac.compare_digest(token, expected):
            return JsonResponse({'error': 'unauthorized'}, status=401)
        return view(request, *args, **kwargs)
    return wrapper


def _product_json(request, p):
    return {
        'id': p.id,
        'name': p.name,
        'brand': p.brand.name,
        'category': p.category.name,
        'category_id': p.category_id,
        'description': p.description,
        'price': int(p.price),
        'final_price': int(p.final_price),
        'is_on_discount': p.is_on_discount,
        'stock': p.stock,
        'image': request.build_absolute_uri(p.image.url) if p.image else None,
    }


def _available_products():
    # Omborda bor va srok godnosti o'tmagan tovarlar
    return (Product.objects.select_related('brand', 'category')
            .filter(stock__gt=0, expiry_date__gte=timezone.now().date()))


@require_GET
@bot_auth
def categories(request):
    data = [{'id': c.id, 'name': c.name} for c in Category.objects.all()]
    return JsonResponse({'results': data})


@require_GET
@bot_auth
def products(request):
    qs = _available_products()
    category = request.GET.get('category')
    if category and category.isdigit():
        qs = qs.filter(category_id=int(category))
    q = request.GET.get('q', '').strip()
    if q:
        from django.db.models import Q
        from .models import SearchQuery
        tg = request.GET.get('tg', '')
        if request.GET.get('page', '1') == '1':
            SearchQuery.objects.create(user_id=int(tg) if tg.isdigit() else None, query_text=q[:200])
        qs = qs.filter(Q(name__icontains=q) | Q(brand__name__icontains=q))

    try:
        page = max(1, int(request.GET.get('page', 1)))
    except ValueError:
        page = 1
    size = 8
    total = qs.count()
    items = qs.order_by('-created_at')[(page - 1) * size: page * size]
    return JsonResponse({
        'results': [_product_json(request, p) for p in items],
        'page': page,
        'has_next': page * size < total,
        'total': total,
    })


@require_GET
@bot_auth
def product_detail(request, product_id):
    try:
        p = _available_products().get(id=product_id)
    except Product.DoesNotExist:
        return JsonResponse({'error': 'not_found'}, status=404)
    return JsonResponse(_product_json(request, p))


@csrf_exempt
@require_POST
@bot_auth
def order_create(request):
    """
    Kutilgan JSON:
    {
      "telegram_user_id": "123", "telegram_username": "ali",
      "customer_name": "Ali", "customer_phone": "+998901234567",
      "payment_method": "cash",            # click | payme | cash
      "discount_amount": 0,                # ixtiyoriy
      "items": [{"product_id": 1, "quantity": 2}]
    }
    Stock bu yerda kamaymaydi: admin buyurtmani "To'landi" qilganda
    Order.finalize_payment() Sale yaratadi va stockni kamaytiradi.
    """
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'error': 'bad_json'}, status=400)

    items = data.get('items') or []
    if not items:
        return JsonResponse({'error': 'empty_items'}, status=400)

    payment_method = data.get('payment_method', 'cash')
    if payment_method not in ('click', 'payme', 'cash'):
        return JsonResponse({'error': 'bad_payment_method'}, status=400)

    try:
        discount = Decimal(str(data.get('discount_amount') or 0))
    except InvalidOperation:
        return JsonResponse({'error': 'bad_discount'}, status=400)
    if discount < 0:
        discount = Decimal(0)

    # Mahsulotlarni tekshirish
    prepared = []
    for row in items:
        try:
            pid = int(row['product_id'])
            qty = int(row['quantity'])
        except (KeyError, TypeError, ValueError):
            return JsonResponse({'error': 'bad_item'}, status=400)
        if qty < 1:
            return JsonResponse({'error': 'bad_quantity'}, status=400)
        try:
            product = _available_products().get(id=pid)
        except Product.DoesNotExist:
            return JsonResponse({'error': 'product_unavailable', 'product_id': pid}, status=409)
        if qty > product.stock:
            return JsonResponse({
                'error': 'not_enough_stock', 'product_id': pid,
                'name': product.name, 'stock': product.stock,
            }, status=409)
        prepared.append((product, qty))

    with transaction.atomic():
        order = Order.objects.create(
            telegram_user_id=str(data.get('telegram_user_id') or '')[:50] or None,
            telegram_username=str(data.get('telegram_username') or '')[:100] or None,
            customer_name=str(data.get('customer_name') or '')[:150] or None,
            customer_phone=str(data.get('customer_phone') or '')[:30] or None,
            payment_method=payment_method,
            discount_amount=discount,
            status='pending',
        )
        for product, qty in prepared:
            OrderItem.objects.create(order=order, product=product, quantity=qty,
                                     unit_price=product.final_price)
        order.recalculate_total()
        order.transaction_id = f"tg-{order.id}-{int(time.time())}"
        order.save(update_fields=['transaction_id'])
        order.refresh_from_db()

    return JsonResponse({
        'id': order.id,
        'status': order.status,
        'total_amount': int(order.total_amount),
        'discount_amount': int(order.discount_amount),
        'items': [{'name': i.product.name, 'quantity': i.quantity, 'unit_price': int(i.unit_price)}
                  for i in order.items.select_related('product')],
    }, status=201)


@require_GET
@bot_auth
def order_status(request, order_id):
    try:
        order = Order.objects.get(id=order_id)
    except Order.DoesNotExist:
        return JsonResponse({'error': 'not_found'}, status=404)
    return JsonResponse({
        'id': order.id,
        'status': order.status,
        'status_display': order.get_status_display(),
        'total_amount': int(order.total_amount),
    })


@require_GET
@bot_auth
def stats(request):
    """Admin statistikasi (botdagi 'Statistika' tugmasi uchun)."""
    from django.db.models import Count, Sum
    from .models import Sale, SearchQuery

    sales = list(Sale.objects.select_related('product'))
    top_sales = (Sale.objects.values('product__name')
                 .annotate(qty=Sum('quantity')).order_by('-qty')[:10])
    top_queries = (SearchQuery.objects.values('query_text')
                   .annotate(c=Count('id')).order_by('-c')[:5])
    return JsonResponse({
        'revenue': int(sum(s.total_revenue for s in sales)),
        'profit': int(sum(s.total_profit for s in sales)),
        'top_sales': [{'name': r['product__name'], 'qty': r['qty']} for r in top_sales],
        'top_queries': [{'text': r['query_text'], 'count': r['c']} for r in top_queries],
    })


@csrf_exempt
@require_POST
@bot_auth
def ai_advice(request):
    """AI maslahatchi: faqat saytdagi mavjud mahsulotlardan tavsiya beradi."""
    import os
    from google import genai

    try:
        data = json.loads(request.body)
        message = str(data.get('message', '')).strip()
        history = data.get('history', [])
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'error': 'bad_json'}, status=400)
    if not message:
        return JsonResponse({'error': 'empty'}, status=400)

    no_concern = "ko'rsatilmagan"
    lines = [
        f"- {p.name} | Brend: {p.brand.name} | Turi: {p.category.name} | "
        f"Narxi: {int(p.final_price)} so'm | Muammo: {p.skin_concern or no_concern}"
        for p in _available_products()
    ]
    if not lines:
        return JsonResponse({'reply': 'Hozircha mahsulotlar mavjud emas.'})

    prompt = (
        "Sen \"Cosmetic Store\" AI kosmetologisan. FAQAT quyidagi ro'yxatdagi mahsulotlardan, "
        "mijoz muammosiga mos kelganini o'zbek tilida, qisqa va samimiy tavsiya qil. "
        "Mos mahsulot bo'lmasa, ochiq ayt. Bir nechta bo'lsa, to'plam tuz va umumiy narxni ayt. "
        "Mijoz so'rovi noaniq bo'lsa, 1-2 ta aniqlashtiruvchi savol ber.\n\n"
        "MAHSULOTLAR:\n" + "\n".join(lines) + "\n\nSUHBAT:\n"
    )
    for h in history[-10:]:
        role = 'Mijoz' if h.get('role') == 'user' else 'Yordamchi'
        prompt += f"{role}: {h.get('text', '')}\n"
    prompt += f"Mijoz: {message}\nYordamchi:"

    try:
        client = genai.Client(api_key=os.getenv('GEMINI_API_KEY'))
        resp = client.models.generate_content(model='gemini-3.6-flash', contents=prompt)
        return JsonResponse({'reply': resp.text})
    except Exception as e:
        t = str(e)
        if '503' in t or 'UNAVAILABLE' in t or '429' in t or 'RESOURCE_EXHAUSTED' in t:
            return JsonResponse({'reply': "Hozir AI band, biroz kutib qayta urinib ko'ring. 🙏"})
        return JsonResponse({'error': 'ai_error'}, status=500)