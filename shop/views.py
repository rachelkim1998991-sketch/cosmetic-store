import os
import json
from google import genai

from django.shortcuts import render
from django.db.models import Q
from .models import Product,Category,Brand,Favorite,CartItem
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST


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
5. Bir nechta mahsulot tavsiya qilishing mumkin, lekin 3 tadan oshirma.
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