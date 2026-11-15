from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class Category(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='categories/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name_plural = "Categories"

class Product(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products')
    name = models.CharField(max_length=200)
    description = models.TextField()
    base_price = models.DecimalField(max_digits=10, decimal_places=2)
    customization_price = models.DecimalField(max_digits=10, decimal_places=2, default=50.00)
    image = models.ImageField(upload_to='products/')
    is_customizable = models.BooleanField(default=True)
    stock = models.IntegerField(default=0)
    is_featured = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    seller = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    parent_product = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True)
    
    def __str__(self):
        return self.name

class Customization(models.Model):
    POSITION_CHOICES = [
        ('front', 'Front Center'),
        ('back', 'Back Center'),
        ('left_chest', 'Left Chest'),
        ('right_chest', 'Right Chest'),
        ('left_sleeve', 'Left Sleeve'),
        ('right_sleeve', 'Right Sleeve'),
    ]
    
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    text = models.CharField(max_length=100, blank=True)
    text_color = models.CharField(max_length=20, default='#000000')
    icon = models.CharField(max_length=10, blank=True)
    icon_color = models.CharField(max_length=20, default='#F28735')
    position = models.CharField(max_length=20, choices=POSITION_CHOICES, default='front')
    font_size = models.IntegerField(default=30)
    preview_image = models.ImageField(upload_to='customizations/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    seller_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    def __str__(self):
        return f"Customization for {self.product.name}"

class Cart(models.Model):  # Fixed: removed "cl" from "clclass"
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    customization = models.ForeignKey(Customization, on_delete=models.SET_NULL, null=True, blank=True)
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    added_at = models.DateTimeField(auto_now_add=True)
    
    # Fields to store customization data directly
    custom_text = models.CharField(max_length=100, null=True, blank=True)
    text_color = models.CharField(max_length=20, null=True, blank=True)
    text_size = models.IntegerField(null=True, blank=True)
    text_x = models.IntegerField(null=True, blank=True)
    text_y = models.IntegerField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.user.username}'s Cart - {self.product.name}"
    
    def get_subtotal(self):
        price = self.product.base_price
        if self.custom_text:
            price += 50
        return price * self.quantity

class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    ]
    
    PAYMENT_STATUS = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    order_date = models.DateTimeField(default=timezone.now)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    shipping_address = models.TextField()
    phone = models.CharField(max_length=15)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default='pending')
    payment_method = models.CharField(max_length=50, default='Cash on Delivery')
    tracking_id = models.CharField(max_length=100, null=True, blank=True)
    courier = models.CharField(max_length=50, null=True, blank=True)
    def __str__(self):
        return f"Order #{self.id} by {self.user.username}"

class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    customization = models.ForeignKey(Customization, on_delete=models.SET_NULL, null=True, blank=True)
    quantity = models.IntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    
    def __str__(self):
        return f"{self.quantity}x {self.product.name}"

class ChatHistory(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    message = models.TextField()
    response = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Chat with {self.user.username} at {self.created_at}"
    

    
class Address(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=15)
    address_line = models.TextField()
    city = models.CharField(max_length=100)
    pincode = models.CharField(max_length=10)

    def __str__(self):
        return self.name
    


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)

    role = models.CharField(
        max_length=10,
        choices=[
            ("admin", "Admin"),
            ("seller", "Seller"),
            ("user", "User")
        ],
        default="user"
    )

    is_approved = models.BooleanField(default=False)
    proof = models.ImageField(upload_to='seller_proofs/', null=True, blank=True)


# ✅ MOVE THIS OUTSIDE
class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    message = models.CharField(max_length=255)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.message
    

class Feedback(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    message = models.TextField()
    rating = models.IntegerField(default=5)  # optional ⭐
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.rating}"
    

class Payment(models.Model):
    PAYMENT_METHODS = (
        ('COD', 'Cash on Delivery'),
        ('ONLINE', 'Online Payment'),
    )

    PAYMENT_STATUS = (
        ('PENDING', 'Pending'),
        ('COMPLETED', 'Completed'),
    )

    order = models.OneToOneField('Order', on_delete=models.CASCADE)
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE)

    method = models.CharField(max_length=10, choices=PAYMENT_METHODS)
    status = models.CharField(max_length=10, choices=PAYMENT_STATUS, default='PENDING')

    amount = models.DecimalField(max_digits=10, decimal_places=2)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Payment #{self.id} - {self.method}"
    
