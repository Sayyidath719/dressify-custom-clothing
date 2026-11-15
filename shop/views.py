# shop/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.contrib import messages
from django.contrib.auth.models import User
from django.db.models import Q
import json
from django.conf import settings

from .models import *
from .utils import process_chat_message

import base64
from django.core.files.base import ContentFile

from .models import Address
from .models import Profile
from .models import Category
from .models import Product
from .models import Order
from .models import Feedback


# HOME PAGE
def home(request):
    products = Product.objects.filter(is_featured=True)
    categories = Category.objects.all()
    feedbacks = Feedback.objects.all().order_by('-created_at')

    return render(request, 'shop/index.html', {
        'products': products,
        'categories': categories,
        'feedbacks': feedbacks
    })


# PRODUCT LIST
def product_list(request):
    category_id = request.GET.get('category')
    search_query = request.GET.get('search', '')

    products = Product.objects.all()

    if category_id:
        products = products.filter(category_id=category_id)

    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query)
        )

    categories = Category.objects.all()

    return render(request, 'shop/product_list.html', {
        'products': products,
        'categories': categories,
        'search_query': search_query,
        'hide_footer': True
    })


# PRODUCT DETAIL
def product_detail(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    return render(request, 'shop/product_detail.html', {'product': product})


# CUSTOMIZE PRODUCT
@login_required
def customize_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    if request.method == 'POST':

        # 🔹 GET DATA
        text = request.POST.get('custom_text', '')
        text_color = request.POST.get('text_color', '#000000')
        icon_src = request.POST.get('icon_src', '')
        preview_image_data = request.POST.get("preview_image")

        icon_x = request.POST.get('icon_x', '150')
        icon_y = request.POST.get('icon_y', '200')
        text_x = request.POST.get('text_x', '50')
        text_y = request.POST.get('text_y', '50')

        text_size = request.POST.get('text_size_value', '30px')
        drawing_data = request.POST.get('drawing_data', '')

        # 🔹 FONT SIZE FIX
        font_size = 30
        try:
            font_size = int(text_size.replace('px', ''))
        except:
            pass

        # 🔥 IMAGE CONVERT (INSIDE POST)
        image_file = None

        if preview_image_data:
            format, imgstr = preview_image_data.split(';base64,')
            ext = format.split('/')[-1]

            image_file = ContentFile(
                base64.b64decode(imgstr),
                name=f'preview_{request.user.id}.{ext}'
            )

        # 🔹 CREATE CUSTOMIZATION
        customization = Customization.objects.create(
            product=product,
            user=request.user,
            text=text,
            text_color=text_color,
            icon=icon_src,
            position='front',
            font_size=font_size,
            preview_image=image_file
        )

        # 🔥 SAVE IMAGE PROPERLY
        if image_file:
            customization.preview_image.save(
                image_file.name,
                image_file,
                save=True
            )

        # 🔹 SAVE SESSION
        request.session['last_customization'] = {
            'text': text,
            'text_color': text_color,
            'text_size': font_size,
            'text_x': text_x,
            'text_y': text_y,
            'icon': icon_src,
            'icon_x': icon_x,
            'icon_y': icon_y,
            'drawing': drawing_data
        }

        # 🔹 SELLER PRICE
        seller_price = request.POST.get("seller_price")
        if seller_price:
            try:
                seller_price = float(seller_price)
            except:
                seller_price = product.base_price

        action = request.POST.get("action")
        mode = request.POST.get("mode")

        # =======================
        # 🧑‍💼 SELLER FLOW
        # =======================
        if mode == "seller" and action == "save":

            new_product = Product.objects.create(
                name=product.name + " (Custom)",
                base_price=seller_price if seller_price else product.base_price,
                customization_price=product.customization_price,
                seller=request.user,
                parent_product=product,
                description=f"Custom: {text}",
                category=product.category,
            )

            # ✅ IMAGE SAVE (INSIDE BLOCK)
            if customization.preview_image:
              new_product.image.save(
            customization.preview_image.name,
            customization.preview_image,
            save=True
        )
                    
            elif product.image:
                new_product.image = product.image
                new_product.save()

            return redirect("seller_dashboard")

        # =======================
        # 👁 USER FLOW
        # =======================
        return redirect(f'/preview/{customization.id}/?mode={mode}')

    # =======================
    # GET (LOAD PAGE)
    # =======================
    mode = request.GET.get("mode")

    return render(request, 'shop/customize.html', {
        'product': product,
        'mode': mode
    })
# PREVIEW DESIGN
@login_required
def preview_design(request, customization_id):
    

    customization = get_object_or_404(Customization, id=customization_id, user=request.user)
    mode = request.GET.get("mode")

    session_data = request.session.get('last_customization', {})

    context = {
        'customization': customization, 'mode': mode,
        'text': session_data.get('text', customization.text),
        'text_color': session_data.get('text_color', customization.text_color),
        'text_size': session_data.get('text_size', customization.font_size),
        'text_x': session_data.get('text_x', '50'),
        'text_y': session_data.get('text_y', '50'),
        'icon': session_data.get('icon', ''),
        'icon_x': session_data.get('icon_x', '150'),
        'icon_y': session_data.get('icon_y', '200'),
        'drawing': session_data.get('drawing', '')
    }

    return render(request, 'shop/preview_design.html', context)


# ADD CUSTOMIZED ITEM TO CART
@login_required
def add_to_cart(request, customization_id):

    customization = get_object_or_404(Customization, id=customization_id, user=request.user)

    if request.method == 'POST':

        # -------- SAVE PREVIEW IMAGE --------
        image_data = request.POST.get("design_image")

        if image_data:
            format, imgstr = image_data.split(';base64,')
            ext = format.split('/')[-1]

            file_name = f"design_{customization.id}.{ext}"

            customization.preview_image.save(
                file_name,
                ContentFile(base64.b64decode(imgstr)),
                save=True
            )
        # ------------------------------------

        quantity = int(request.POST.get('quantity', 1))
        session_data = request.session.get('last_customization', {})

        Cart.objects.create(
            user=request.user,
            product=customization.product,
            customization=customization,
            quantity=quantity,
            price=customization.product.base_price + customization.product.customization_price,
            custom_text=customization.text,
            text_color=customization.text_color,
            text_size=customization.font_size,
            text_x=int(float(session_data.get('text_x', 50))),
            text_y=int(float(session_data.get('text_y', 50)))
        )

        messages.success(request, "Customized product added to cart")
        return redirect('cart')

    return render(request, 'shop/add_to_cart.html', {'customization': customization})


# ADD PLAIN PRODUCT TO CART
@login_required
def add_plain_to_cart(request, product_id):

    product = get_object_or_404(Product, id=product_id)

    Cart.objects.create(
        user=request.user,
        product=product,
        quantity=1,
        price=product.base_price
    )

    messages.success(request, "Product added to cart")
    return redirect('cart')


# BUY NOW WITHOUT CUSTOMIZATION
@login_required
def buy_now_plain(request, product_id):

    product = get_object_or_404(Product, id=product_id)

    Cart.objects.create(
        user=request.user,
        product=product,
        quantity=1,
        price=product.base_price
    )

    return redirect('checkout')


# CART
@login_required
def cart(request):

    cart_items = Cart.objects.filter(user=request.user)

    total = 0

    for item in cart_items:
        item.subtotal = item.get_subtotal()
        total += item.subtotal

    return render(request, 'shop/cart.html', {
        'cart_items': cart_items,
        'total': total
    })


# UPDATE CART
@login_required
def update_cart(request, item_id):

    cart_item = get_object_or_404(Cart, id=item_id, user=request.user)

    if request.POST.get('action') == 'remove':
        cart_item.delete()

    else:
        quantity = int(request.POST.get('quantity', 1))

        if quantity > 0:
            cart_item.quantity = quantity
            cart_item.save()
        else:
            cart_item.delete()

    return redirect('cart')


from .models import Cart, Order, OrderItem, Address, Notification   # ✅ ADD Notification

from django.contrib.auth.models import User  # ✅ ADD THIS

@login_required
def checkout(request):

    cart_items = Cart.objects.filter(user=request.user)

    if not cart_items:
        return redirect('product_list')

    total_amount = sum(item.get_subtotal() for item in cart_items)
    addresses = Address.objects.filter(user=request.user)

    if request.method == 'POST':

        address_id = request.POST.get('address')
        selected_address = Address.objects.get(id=address_id)

        shipping_address = selected_address.address_line
        phone = selected_address.phone

        payment_method = request.POST.get('payment_method', 'Cash on Delivery')
        payment_done = request.POST.get('payment_done')

        if payment_method == "Card" and payment_done == "true":
            payment_status = "Paid"
        else:
            payment_status = "Pending"

        # ✅ CREATE ORDER
        order = Order.objects.create(
            user=request.user,
            total_amount=total_amount,
            shipping_address=shipping_address,
            phone=phone,
            payment_method=payment_method,
            payment_status=payment_status
        )
        # ✅ CREATE PAYMENT (ADD THIS)
        Payment.objects.create(
    order=order,
    user=request.user,
    method='COD' if payment_method != "Card" else 'ONLINE',
    amount=order.total_amount,
    status='PENDING' if payment_method != "Card" else 'COMPLETED'
)

        # ✅ ORDER ITEMS
        for item in cart_items:
            OrderItem.objects.create(
                order=order,
                product=item.product,
                customization=item.customization,
                quantity=item.quantity,
                price=item.price
            )

        # ✅ USER NOTIFICATION
        Notification.objects.create(
            user=request.user,
            message=f"Your order #{order.id} has been placed successfully 🛒"
        )

        # ✅ 🔥 ADMIN NOTIFICATION (THIS WAS MISSING)
        admins = User.objects.filter(is_staff=True)

        for admin in admins:
            Notification.objects.create(
                user=admin,
                message=f"New order #{order.id} placed by {request.user.username}"
            )

        cart_items.delete()

        return redirect('orders')

    return render(request, 'shop/checkout.html', {
        'cart_items': cart_items,
        'total': total_amount,
        'addresses': addresses,
        'hide_footer': True
    })


# ORDERS
@login_required
def orders(request):

    orders_list = Order.objects.filter(user=request.user).order_by('-order_date')

    return render(request, 'shop/orders.html', {'orders': orders_list, 'hide_footer': True})

@login_required
def order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    return render(request, 'shop/order_detail.html', {'order': order})

# LOGIN
def user_login(request):

    if request.method == 'POST':

        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(username=username, password=password)

        if user:
            try:
                profile = Profile.objects.get(user=user)

                # 🔴 CHECK BEFORE LOGIN
                if profile.role == "seller" and not profile.is_approved:
                    messages.error(request, "Your seller account is pending approval")
                    return redirect('login')

            except Profile.DoesNotExist:
                profile = None

            # ✅ LOGIN ONLY AFTER CHECK
            login(request, user)

            if user.is_staff:
                return redirect('admin_dashboard')

            if profile and profile.role == "seller":
                return redirect('seller_dashboard')

            return redirect('home')

        else:
            messages.error(request, "Invalid login")

    return render(request, 'shop/login.html', {'hide_footer': True})


# REGISTER
def register(request):

    if request.method == 'POST':

        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')

        # ✅ CHECK PASSWORD MATCH
        if password != confirm_password:
            messages.error(request, "Passwords do not match")
            return redirect('register')

        # ✅ CHECK USERNAME EXISTS
        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists")
            return redirect('register')

        # ✅ CREATE USER
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password
        )
        Profile.objects.create(user=user, role="user", is_approved=True)
        login(request, user)
        return redirect('home')

    return render(request, 'shop/register.html', {'hide_footer': True})


# LOGOUT
def user_logout(request):

    logout(request)
    return redirect('home')

@login_required
def chatbot_api(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            message = data.get('message', '')

            response = process_chat_message(message)

            ChatHistory.objects.create(
                user=request.user,
                message=message,
                response=response['reply']
            )

            return JsonResponse(response)

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)

    return JsonResponse({'error': 'Invalid request'}, status=400)

@login_required
def seller_approval(request):

    if not request.user.is_staff:
        return redirect('home')

    sellers = Profile.objects.filter(role="seller", is_approved=False)

    return render(request, 'shop/seller_approval.html', {
        'sellers': sellers
    })

@login_required
def approve_seller(request, id):
    if request.user.is_staff:
        profile = Profile.objects.get(id=id)
        profile.is_approved = True
        profile.save()
    return redirect('manage_sellers')


@login_required
def reject_seller(request, id):
    if request.user.is_staff:
        profile = Profile.objects.get(id=id)
        profile.user.delete()   # delete fake seller
    return redirect('manage_sellers')

from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import render, redirect
from .models import Order, Product, Notification
from django.contrib.auth.models import User


@login_required
def admin_dashboard(request):
    if not request.user.is_staff:
        messages.error(request, "Access denied")
        return redirect('home')

    # 📊 Stats
    total_orders = Order.objects.count()
    total_products = Product.objects.count()
    total_users = User.objects.count()

    total_revenue = sum(order.total_amount for order in Order.objects.all())

    recent_orders = Order.objects.order_by('-order_date')[:10]

    # 🔔 Notification count
    unread_count = Notification.objects.filter(
        user=request.user,
        is_read=False
    ).count()

    context = {
        'total_orders': total_orders,
        'total_products': total_products,
        'total_users': total_users,
        'total_revenue': total_revenue,
        'recent_orders': recent_orders,
        'unread_count': unread_count,
        'hide_footer': True,
    }

    return render(request, 'shop/admin_dashboard.html', context)
@login_required
def increase_quantity(request, item_id):
    cart_item = get_object_or_404(Cart, id=item_id, user=request.user)
    cart_item.quantity += 1
    cart_item.save()
    return redirect('cart')


@login_required
def decrease_quantity(request, item_id):
    cart_item = get_object_or_404(Cart, id=item_id, user=request.user)

    if cart_item.quantity > 1:
        cart_item.quantity -= 1
        cart_item.save()
    else:
        cart_item.delete()

    return redirect('cart')

@login_required
def remove_from_cart(request, item_id):
    cart_item = get_object_or_404(Cart, id=item_id, user=request.user)
    cart_item.delete()
    messages.success(request, "Item removed from cart.")
    return redirect('cart')



def about(request):
    return render(request,'shop/about.html',{'hide_footer': True})

@login_required
def account(request):
    return render(request, 'shop/account.html', {'hide_footer': True})


@login_required
def delete_account(request):
    user = request.user
    user.delete()
    logout(request)
    return redirect('home')



@login_required
def saved_addresses(request):
    addresses = Address.objects.filter(user=request.user)
    return render(request, 'shop/saved_addresses.html', {'addresses': addresses})


import re   # 👈 add this at top of file

@login_required
def add_address(request):

    next_page = request.GET.get('next')

    if request.method == "POST":
        name = request.POST.get('name')
        phone = request.POST.get('phone')
        address_line = request.POST.get('address_line')
        city = request.POST.get('city')
        pincode = request.POST.get('pincode')

        # ✅ ADD THIS BLOCK 👇
        if not re.match(r'^[A-Za-z ]+$', name):
            messages.error(request, "Name should contain only letters")
            return redirect(request.path)

        # existing code ↓
        if len(phone) != 10 or not phone.isdigit():
            messages.error(request, "Phone number must be 10 digits")
            return redirect(request.path)

        if len(pincode) != 6 or not pincode.isdigit():
            messages.error(request, "Pincode must be 6 digits")
            return redirect(request.path)

        Address.objects.create(
            user=request.user,
            name=name,
            phone=phone,
            address_line=address_line,
            city=city,
            pincode=pincode
        )

        if next_page == "checkout":
            return redirect('checkout')

        return redirect('saved_addresses')

    return render(request, 'shop/add_address.html', {'hide_footer': True})
@login_required
def delete_address(request, id):
    address = Address.objects.get(id=id, user=request.user)
    if request.method == "POST": address.delete()
    return redirect('saved_addresses')




import re  # already added above

def register_seller(request):
    if request.method == "POST":
        username = request.POST.get("username")
        email = request.POST.get("email")
        password = request.POST.get("password")
        phone = request.POST.get("phone")
        proof = request.FILES.get("proof")

        # 🔐 PASSWORD VALIDATION
        if len(password) < 6:
            messages.error(request, "Password must be at least 6 characters")
            return redirect(request.path)

        if not re.search(r'[A-Z]', password):
            messages.error(request, "Add at least 1 uppercase letter")
            return redirect(request.path)

        if not re.search(r'[0-9]', password):
            messages.error(request, "Add at least 1 number")
            return redirect(request.path)

        # 📱 PHONE VALIDATION
        if len(phone) != 10 or not phone.isdigit():
            messages.error(request, "Phone must be 10 digits")
            return redirect(request.path)

        # 👤 CREATE USER
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password
        )

        # 🧑‍💼 CREATE PROFILE WITH PROOF
        Profile.objects.create(
            user=user,
            role="seller",
            is_approved=False,
            proof=proof
        )

        # 🔔 NOTIFICATION FOR ADMIN
        from .models import Notification

        admin_users = User.objects.filter(profile__role="admin")

        for admin in admin_users:
            Notification.objects.create(
                user=admin,
                message=f"New seller '{username}' registered and waiting for approval."
            )

        messages.success(request, "Seller registered successfully!")

        return redirect("login")

    return render(request, "shop/register_seller.html", {'hide_footer': True})


from django.db.models import Sum
from django.db.models.functions import TruncDate, TruncMonth
from .models import Product, OrderItem
from django.conf import settings
from django.contrib.auth.decorators import login_required

@login_required
def seller_dashboard(request):
    user = request.user

    # Existing product logic
    admin_products = Product.objects.filter(seller__isnull=True)
    seller_products = Product.objects.filter(seller=user)

    seller_product_parent_ids = Product.objects.filter(
        seller=user
    ).values_list('parent_product_id', flat=True)

    # 🔥 NEW ANALYTICS
    order_items = OrderItem.objects.filter(product__seller=user)

    seller_orders = Order.objects.filter(
        items__product__seller=user
    ).distinct()

    seller_orders_with_earnings = []

    # ✅ FIXED LOOP (INSIDE FUNCTION)
    for order in seller_orders:
        seller_total = 0

        for item in order.items.all():
            if item.product.seller == user:
                seller_total += item.price * settings.SELLER_PERCENT / 100

        seller_orders_with_earnings.append({
            "order": order,
            "seller_total": seller_total
        })

    # ✅ COUNTS
    total_products = seller_products.count()
    total_orders = order_items.values('order').distinct().count()

    # 🔥 REVENUE LOGIC
    total_revenue = 0
    daily_earnings = []
    monthly_earnings = []

    for item in order_items:
        seller_share = item.price * settings.SELLER_PERCENT / 100
        total_revenue += seller_share

        # DAILY
        date = item.order.order_date.date()
        found = False
        for d in daily_earnings:
            if d["date"] == date:
                d["total"] += seller_share
                found = True
                break
        if not found:
            daily_earnings.append({
                "date": date,
                "total": seller_share
            })

        # MONTHLY
        month = item.order.order_date.strftime("%Y-%m")
        found = False
        for m in monthly_earnings:
            if m["month"] == month:
                m["total"] += seller_share
                found = True
                break
        if not found:
            monthly_earnings.append({
                "month": month,
                "total": seller_share
            })

    return render(request, "shop/seller_dashboard.html", {
        "admin_products": admin_products,
        "seller_products": seller_products,
        "seller_product_parent_ids": seller_product_parent_ids,
        "seller_orders": seller_orders_with_earnings,

        "total_products": total_products,
        "total_orders": total_orders,
        "total_revenue": total_revenue,
        "daily_earnings": daily_earnings,
        "monthly_earnings": monthly_earnings,

        "hide_footer": True
    })

@login_required
def add_product(request):
    categories = Category.objects.all()

    if request.method == "POST":
        name = request.POST.get("name")
        price = request.POST.get("price")
        category_id = request.POST.get("category")

        Product.objects.create(
            name=name,
            base_price=price,
            category_id=category_id,  # 🔥 IMPORTANT
            seller=request.user
        )

        return redirect("seller_dashboard")

    return render(request, "shop/add_product.html", {
        "categories": categories
    })

@login_required
def add_to_seller(request, product_id):
    from django.shortcuts import get_object_or_404

    admin_product = get_object_or_404(Product, id=product_id)
    # 🚫 prevent duplicate
    if Product.objects.filter(parent_product=admin_product, seller=request.user).exists():
        return redirect("seller_dashboard")


    Product.objects.create(
        name=admin_product.name,
        description=admin_product.description,
        base_price=admin_product.base_price,
        image=admin_product.image,
        category=admin_product.category,
        seller=request.user,
        parent_product=admin_product   # 🔥 LINK
    )

    return redirect("seller_dashboard")

from django.shortcuts import get_object_or_404

def remove_seller_product(request, product_id):
    product = get_object_or_404(Product, id=product_id, seller=request.user)
    product.delete()
    return redirect("seller_dashboard")

from django.core.files.base import ContentFile

@login_required
def save_custom_product(request, customization_id):
    customization = get_object_or_404(Customization, id=customization_id)
    product = customization.product

    new_product = Product.objects.create(
        name=product.name + " (Custom)",
        base_price=product.base_price,
        customization_price=product.customization_price,
        seller=request.user,
        parent_product=product,
        description=f"Custom: {customization.text}",
        category=product.category
    )

    # 🔥 FORCE SAVE IMAGE CORRECTLY
    if customization.preview_image:
        new_product.image.save(
            customization.preview_image.name,
            customization.preview_image,
            save=True
        )
    elif product.image:
        new_product.image = product.image
        new_product.save()

    return redirect("seller_dashboard")

def browse_products(request):
    admin_products = Product.objects.filter(seller__isnull=True)

    seller_products = Product.objects.filter(
        seller=request.user,
        parent_product__isnull=False   # 🔥 IMPORTANT
    )

    seller_product_parent_ids = [
        p.parent_product.id for p in seller_products
    ]

    return render(request, "shop/browse_products.html", {
        "admin_products": admin_products,
        "seller_product_parent_ids": seller_product_parent_ids
    })

def manage_order(request, order_id):
    order = Order.objects.get(id=order_id)

    if request.method == 'POST':
        new_status = request.POST.get('status')
        tracking_id = request.POST.get('tracking_id')
        courier = request.POST.get('courier')

        order.status = new_status
        order.tracking_id = tracking_id
        order.courier = courier
        order.save()

        # ✅ MOVE THIS INSIDE
        if new_status == "delivered":
            payment = Payment.objects.get(order=order)
            payment.status = "COMPLETED"
            payment.save()

    return render(request, 'shop/manage_order.html', {
        'order': order,
        'hide_footer': True
    })

def add_product_custom(request):
    from .models import Product, Category

    categories = Category.objects.all()

    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description')
        price = request.POST.get('price')
        category_id = request.POST.get('category')
        image = request.FILES.get('image')
        is_customizable = request.POST.get('is_customizable') == 'on'

        category = Category.objects.get(id=category_id)

        Product.objects.create(
            name=name,
            description=description,
            base_price=price,
            category=category,
            image=image,
            is_customizable=is_customizable
        )

        return redirect('admin_dashboard')  # after adding product

    return render(request, 'shop/add_product.html', {
        'categories': categories ,'hide_footer':True
    })

def add_category(request):
    from .models import Category

    if request.method == 'POST':
        name = request.POST.get('name')

        Category.objects.create(name=name)

        return redirect('admin_dashboard')

    return render(request, 'shop/add_category.html' ,{'hide_footer':True})

def all_orders(request):
    orders = Order.objects.all()
    return render(request, 'shop/all_orders.html', {'orders': orders ,'hide_footer':True})

def manage_users(request):
    users = User.objects.all()
    return render(request, 'shop/manage_users.html', {'users': users  , 'hide_footer':True})

def make_admin(request, user_id):
    user = User.objects.get(id=user_id)
    user.is_staff = True
    user.save()
    return redirect('manage_users')


def delete_user(request, user_id):
    user = User.objects.get(id=user_id)
    user.delete()
    return redirect('manage_users')


def manage_sellers(request):
    from django.contrib.auth.models import User
    from .models import Profile

    sellers = Profile.objects.filter(role="seller")
    pending_sellers = Profile.objects.filter(role="seller", is_approved=False)

    return render(request, 'shop/manage_sellers.html', {
    'sellers': sellers,
    'pending_sellers': pending_sellers,
    'hide_footer': True
})

def remove_seller(request, user_id):
    from django.contrib.auth.models import User
    from .models import Profile

    user = User.objects.get(id=user_id)
    profile = Profile.objects.get(user=user)

    profile.role = "user"
    profile.save()

    return redirect('manage_sellers')

@login_required
def notifications_view(request):
    notifications = Notification.objects.filter(user=request.user).order_by('-created_at')

    # mark as read
    notifications.update(is_read=True)

    return render(request, 'shop/notifications.html', {
        'notifications': notifications, 'hide_footer': True
    })


@login_required
def feedback(request):
    if request.method == "POST":
        message = request.POST.get("message")
        rating = request.POST.get("rating")

        Feedback.objects.create(
            user=request.user,
            message=message,
            rating=rating
        )

        return redirect('home')

    return render(request, 'shop/feedback.html')

@login_required
def admin_feedbacks(request):
    if not request.user.is_staff:
        return redirect('home')

    feedbacks = Feedback.objects.all().order_by('-created_at')

    return render(request, 'shop/admin_feedbacks.html', {
        'feedbacks': feedbacks,
        'hide_footer': True
    })

from .models import Feedback, Notification

@login_required
def submit_feedback(request):
    if request.method == "POST":
        message = request.POST.get("message")
        rating = int(request.POST.get("rating"))

        Feedback.objects.create(
            user=request.user,
            message=message,
            rating=rating
        )

        # 🔥 CREATE NOTIFICATION
        if rating <= 2:
            Notification.objects.create(
                user=request.user,
                message="😔 We're sorry for your experience. We will improve!"
            )
        else:
            Notification.objects.create(
                user=request.user,
                message="😊 We're glad you loved it! Thanks for your feedback!"
            )

    return redirect('home')

from .models import Payment



from django.contrib.auth.decorators import login_required
from .models import Payment

@login_required
def admin_payments(request):
    if not request.user.is_staff:
        return redirect('home')

    payments = Payment.objects.all().order_by('-created_at')

    return render(request, 'shop/admin_payments.html', {
        'payments': payments, 'hide_footer': True
        
    })


from django.conf import settings

def seller_orders(request):
    orders = Order.objects.filter(
        items__product__seller=request.user
    ).distinct()

    seller_orders_data = []

    for order in orders:
        seller_total = 0

        for item in order.items.all():
            if item.product.seller == request.user:
                seller_total += item.price * item.quantity

        # apply seller percentage
        seller_total = seller_total * settings.SELLER_PERCENT / 100

        seller_orders_data.append({
            'order': order,
            'seller_total': seller_total
        })

    return render(request, 'shop/seller_orders.html', {
        'orders_data': seller_orders_data
    })


def seller_products(request):
    products = Product.objects.filter(seller=request.user)
    return render(request, 'shop/seller_products.html', {'products': products, 'hide_footer': True})

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from decimal import Decimal
from django.conf import settings

from decimal import Decimal
from django.conf import settings

@login_required
def seller_earnings(request):
    orders = Order.objects.filter(
        items__product__seller=request.user
    ).distinct()

    orders_data = []
    total_earnings = Decimal('0.00')

    daily_data = {}
    monthly_data = {}

    for order in orders:
        seller_total = Decimal('0.00')

        for item in order.items.all():
            if item.product.seller == request.user:
                seller_total += item.price * item.quantity

        seller_total = seller_total * Decimal(settings.SELLER_PERCENT) / Decimal(100)

        # total
        total_earnings += seller_total

        # daily
        date = order.order_date.date()
        daily_data[date] = daily_data.get(date, 0) + seller_total

        # monthly
        month = order.order_date.strftime('%Y-%m')
        monthly_data[month] = monthly_data.get(month, 0) + seller_total

        orders_data.append({
            'order': order,
            'seller_total': seller_total
        })

    return render(request, 'shop/seller_earnings.html', {
        'total_earnings': total_earnings,
        'orders_data': orders_data,
        'daily_data': daily_data,
        'monthly_data': monthly_data,
          'hide_footer': True
    })

from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash
from django.shortcuts import render, redirect
from django.contrib import messages

@login_required
def change_password(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)

        if form.is_valid():
            user = form.save()  # ✅ saves password

            update_session_auth_hash(request, user)  # ✅ must be inside

            messages.success(request, "Password changed successfully!")

            return redirect('account')  # ✅ inside if

    else:
        form = PasswordChangeForm(request.user)

    return render(request, 'shop/change_password.html', {
        'form': form,
        'hide_footer': True
    })
@login_required
def seller_feedbacks(request):
    if not request.user.profile.role == "seller":
        return redirect('home')

    feedbacks = Feedback.objects.all().order_by('-created_at')

    return render(request, 'shop/seller_feedbacks.html', {
        'feedbacks': feedbacks,
        'hide_footer': True
    })