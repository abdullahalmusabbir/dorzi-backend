import uuid
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone


# ─────────────────────────────────────────
#  CHOICES
# ─────────────────────────────────────────

class GenderChoice(models.TextChoices):
    MALE   = 'male',   'Male'
    FEMALE = 'female', 'Female'
    OTHER  = 'other',  'Other'


class OrderStatusChoice(models.TextChoices):
    PENDING    = 'pending',    'Pending'
    CONFIRMED  = 'confirmed',  'Confirmed'
    PROCESSING = 'processing', 'Processing'
    SHIPPED    = 'shipped',    'Shipped'
    DELIVERED  = 'delivered',  'Delivered'
    CANCELLED  = 'cancelled',  'Cancelled'


class PaymentStatusChoice(models.TextChoices):
    UNPAID     = 'unpaid',     'Unpaid'
    PARTIAL    = 'partial',    'Partial'
    PAID       = 'paid',       'Paid'
    REFUNDED   = 'refunded',   'Refunded'


class PaymentMethodChoice(models.TextChoices):
    CASH       = 'cash',       'Cash'
    BKASH      = 'bkash',      'bKash'
    NAGAD      = 'nagad',      'Nagad'
    CARD       = 'card',       'Card'
    BANK       = 'bank',       'Bank Transfer'


class FabricTypeChoice(models.TextChoices):
    COTTON     = 'cotton',     'Cotton'
    SILK       = 'silk',       'Silk'
    LINEN      = 'linen',      'Linen'
    POLYESTER  = 'polyester',  'Polyester'
    WOOL       = 'wool',       'Wool'
    DENIM      = 'denim',      'Denim'
    GEORGETTE  = 'georgette',  'Georgette'
    CHIFFON    = 'chiffon',    'Chiffon'
    OTHER      = 'other',      'Other'


class EmbroideryTypeChoice(models.TextChoices):
    NAKSHI     = 'nakshi',     'Nakshi'
    ZARDOZI    = 'zardozi',    'Zardozi'
    THREAD     = 'thread',     'Thread Work'
    MIRROR     = 'mirror',     'Mirror Work'
    PATCH      = 'patch',      'Patch Work'
    OTHER      = 'other',      'Other'


class NotificationTypeChoice(models.TextChoices):
    ORDER      = 'order',      'Order'
    MESSAGE    = 'message',    'Message'
    REVIEW     = 'review',     'Review'
    PAYMENT    = 'payment',    'Payment'
    SYSTEM     = 'system',     'System'


# ─────────────────────────────────────────
#  1. CUSTOMER
# ─────────────────────────────────────────

class Customer(models.Model):
    user = models.OneToOneField(User,on_delete=models.CASCADE,related_name='customer',null=True,blank=True,)
    profile_picture = models.ImageField(upload_to='customers/profile_pictures/',null=True,blank=True,)
    phone_number = models.CharField(max_length=15, unique=True)
    gender = models.CharField(max_length=10,choices=GenderChoice.choices,default=GenderChoice.MALE,)
    date_of_birth = models.DateField(null=True, blank=True)
    address = models.TextField(null=True, blank=True)
    city = models.CharField(max_length=100, null=True, blank=True)
    district = models.CharField(max_length=100, null=True, blank=True)
    postal_code = models.CharField(max_length=10, null=True, blank=True)

    # Body measurements (cm) — used for tailor_order
    chest = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    waist = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    hip = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    shoulder = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    sleeve = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    neck = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    inseam = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    height = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    weight = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Customer'
        verbose_name_plural = 'Customers'
        indexes = [
            models.Index(fields=['phone_number']),
            models.Index(fields=['city', 'district']),
        ]

    def __str__(self):
        return f"Customer → {self.user.get_full_name() or self.user.username}"


# ─────────────────────────────────────────
#  2. TAILOR
# ─────────────────────────────────────────

class Tailor(models.Model):
    user = models.OneToOneField(User,on_delete=models.CASCADE,related_name='tailor',null=True,blank=True,)
    profile_picture = models.ImageField(upload_to='tailors/profile_pictures/',null=True,blank=True,)
    shop_name = models.CharField(max_length=200)
    shop_logo = models.ImageField(upload_to='tailors/shop_logos/',null=True,blank=True,)
    shop_banner = models.ImageField(upload_to='tailors/shop_banners/',null=True,blank=True,)
    shop_description = models.TextField(null=True, blank=True)
    phone_number = models.CharField(max_length=15, unique=True)
    whatsapp_number  = models.CharField(max_length=15, null=True, blank=True)
    gender = models.CharField(max_length=10,choices=GenderChoice.choices,default=GenderChoice.MALE,blank=True,null=True,)
    address = models.TextField()
    city = models.CharField(max_length=100)
    district = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=10, null=True, blank=True)

    # Experience & Skills
    experience_years = models.PositiveSmallIntegerField(default=0)
    specializations  = models.JSONField(default=list, blank=True)
    # e.g. ["saree_blouse", "salwar_kameez", "suit", "wedding_dress"]

    # Business
    nid_number = models.CharField(max_length=20, unique=True, null=True, blank=True)
    trade_license = models.CharField(max_length=50, null=True, blank=True)
    bkash_number = models.CharField(max_length=15, null=True, blank=True)
    nagad_number = models.CharField(max_length=15, null=True, blank=True)
    bank_account = models.CharField(max_length=30, null=True, blank=True)

    # Rating cache — updated via signals (avoid heavy aggregation on every request)
    average_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.00,validators=[MinValueValidator(0), MaxValueValidator(5)],)
    total_reviews = models.PositiveIntegerField(default=0)
    total_orders = models.PositiveIntegerField(default=0)
    completed_orders = models.PositiveIntegerField(default=0)

    is_verified = models.BooleanField(default=False)
    is_active_shop = models.BooleanField(default=True)
    is_available = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = 'Tailor'
        verbose_name_plural = 'Tailors'
        indexes = [
            models.Index(fields=['city', 'district']),
            models.Index(fields=['is_verified', 'is_active_shop']),
            models.Index(fields=['average_rating']),
        ]

    def __str__(self):
        return f"Tailor → {self.shop_name} ({self.user.username})"


# ─────────────────────────────────────────
#  3. FABRIC
# ─────────────────────────────────────────

class Fabric(models.Model):
    tailor = models.ForeignKey(Tailor,on_delete=models.SET_NULL,related_name='fabrics',null=True,blank=True,)
    name = models.CharField(max_length=200)
    fabric_type = models.CharField(max_length=20,choices=FabricTypeChoice.choices,default=FabricTypeChoice.COTTON,)
    description = models.TextField(null=True, blank=True)
    color = models.CharField(max_length=50, null=True, blank=True)
    pattern = models.CharField(max_length=100, null=True, blank=True)
    # e.g. "floral", "plain", "checkered", "striped"
    image = models.ImageField(upload_to='fabrics/',null=True,blank=True,)
    price_per_yard = models.DecimalField(max_digits=10, decimal_places=2,validators=[MinValueValidator(0)],)
    stock_yards = models.DecimalField(max_digits=8, decimal_places=2, default=0,validators=[MinValueValidator(0)],)
    is_available = models.BooleanField(default=True)
    created_at   = models.DateTimeField(auto_now_add=True)
    updated_at   = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = 'Fabric'
        verbose_name_plural = 'Fabrics'
        indexes = [
            models.Index(fields=['tailor', 'is_available']),
            models.Index(fields=['fabric_type']),
        ]

    def __str__(self):
        return f"{self.name} ({self.get_fabric_type_display()}) — {self.tailor.shop_name}"


# ─────────────────────────────────────────
#  4. EMBROIDERY
# ─────────────────────────────────────────

class Embroidery(models.Model):
    tailor = models.ForeignKey(Tailor,on_delete=models.SET_NULL,related_name='embroideries',null=True,blank=True,)
    name = models.CharField(max_length=200)
    embroidery_type = models.CharField(max_length=20,choices=EmbroideryTypeChoice.choices,default=EmbroideryTypeChoice.THREAD,)
    description  = models.TextField(null=True, blank=True)
    sample_image = models.ImageField(upload_to='embroideries/',null=True,blank=True,)
    price = models.DecimalField(max_digits=10, decimal_places=2,validators=[MinValueValidator(0)],)
    # Estimated extra days this embroidery adds to delivery
    extra_days       = models.PositiveSmallIntegerField(default=0)
    is_available     = models.BooleanField(default=True)
    created_at       = models.DateTimeField(auto_now_add=True)
    updated_at       = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = 'Embroidery'
        verbose_name_plural = 'Embroideries'
        indexes = [
            models.Index(fields=['tailor', 'is_available']),
            models.Index(fields=['embroidery_type']),
        ]

    def __str__(self):
        return f"{self.name} — {self.tailor.shop_name}"


# ─────────────────────────────────────────
#  5. PRE-DESIGNED DRESS  (PreDress)
# ─────────────────────────────────────────

class PreDress(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tailor = models.ForeignKey(Tailor,on_delete=models.SET_NULL,related_name='pre_dresses',null=True,blank=True,)
    title = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    category = models.CharField(max_length=100)
    # e.g. "saree_blouse", "salwar_kameez", "lehenga", "suit", "panjabi"

    sizes_available = models.JSONField(default=list)
    # e.g. ["XS","S","M","L","XL","XXL"] or custom sizes

    colors_available = models.JSONField(default=list)
    # e.g. ["red","blue","#FF5733"]

    fabric = models.ForeignKey(Fabric,on_delete=models.SET_NULL,null=True,blank=True,related_name='pre_dresses',)
    embroidery  = models.ForeignKey(Embroidery,on_delete=models.SET_NULL,null=True,blank=True,related_name='pre_dresses',)
    price = models.DecimalField(max_digits=10, decimal_places=2,validators=[MinValueValidator(0)],)
    discount_price = models.DecimalField(max_digits=10, decimal_places=2,null=True, blank=True,validators=[MinValueValidator(0)],)
    stock_quantity = models.PositiveIntegerField(default=0)
    delivery_days = models.PositiveSmallIntegerField(default=7)

    # SEO / search
    tags = models.JSONField(default=list, blank=True)
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)

    # Cache
    average_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.00,)
    total_reviews  = models.PositiveIntegerField(default=0)
    total_sold = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = 'Pre-Designed Dress'
        verbose_name_plural = 'Pre-Designed Dresses'
        indexes = [
            models.Index(fields=['tailor', 'is_active']),
            models.Index(fields=['category']),
            models.Index(fields=['is_featured']),
            models.Index(fields=['price']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"{self.title} — {self.tailor.shop_name}"

    @property
    def effective_price(self):
        return self.discount_price if self.discount_price else self.price


class PreDressImage(models.Model):
    pre_dress = models.ForeignKey(PreDress,on_delete=models.SET_NULL,null=True,blank=True,related_name='images',)
    image = models.ImageField(upload_to='pre_dresses/images/')
    is_primary = models.BooleanField(default=False)
    order = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering            = ['order']
        verbose_name        = 'Pre-Dress Image'
        verbose_name_plural = 'Pre-Dress Images'

    def __str__(self):
        return f"Image for {self.pre_dress.title}"


# ─────────────────────────────────────────
#  6. PRE-DRESS ORDER
# ─────────────────────────────────────────

class PreDressOrder(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order_number = models.CharField(max_length=20, unique=True, editable=False)
    customer = models.ForeignKey(Customer,on_delete=models.SET_NULL,null=True,related_name='pre_dress_orders',)
    pre_dress   = models.ForeignKey(PreDress,on_delete=models.SET_NULL,null=True,related_name='orders',)
    tailor = models.ForeignKey(Tailor,on_delete=models.SET_NULL,null=True,related_name='pre_dress_orders',)

    # Order details
    quantity = models.PositiveSmallIntegerField(default=1)
    selected_size = models.CharField(max_length=20, null=True, blank=True)
    selected_color = models.CharField(max_length=50, null=True, blank=True)
    special_note = models.TextField(null=True, blank=True)

    # Pricing snapshot (store at time of order — prices may change)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    delivery_charge = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    grand_total = models.DecimalField(max_digits=10, decimal_places=2)

    # Status
    status = models.CharField(max_length=20,choices=OrderStatusChoice.choices,default=OrderStatusChoice.PENDING,)
    payment_status = models.CharField(max_length=20,choices=PaymentStatusChoice.choices,default=PaymentStatusChoice.UNPAID,)
    payment_method = models.CharField(max_length=20,choices=PaymentMethodChoice.choices,null=True,blank=True,)
    transaction_id = models.CharField(max_length=100, null=True, blank=True)

    # Delivery
    delivery_address = models.TextField()
    delivery_city = models.CharField(max_length=100)
    estimated_delivery_date = models.DateField(null=True, blank=True)
    actual_delivery_date = models.DateField(null=True, blank=True)

    # Timestamps
    ordered_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Pre-Dress Order'
        verbose_name_plural = 'Pre-Dress Orders'
        ordering            = ['-ordered_at']
        indexes = [
            models.Index(fields=['customer', 'status']),
            models.Index(fields=['tailor', 'status']),
            models.Index(fields=['order_number']),
            models.Index(fields=['ordered_at']),
            models.Index(fields=['payment_status']),
        ]

    def save(self, *args, **kwargs):
        if not self.order_number:
            import random, string
            self.order_number = 'PD' + ''.join(
                random.choices(string.digits, k=10)
            )
        super().save(*args, **kwargs)

    def __str__(self):
        return f"PreDressOrder #{self.order_number}"


# ─────────────────────────────────────────
#  7. TAILOR ORDER  (Custom Stitching)
# ─────────────────────────────────────────

class TailorOrder(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order_number = models.CharField(max_length=20, unique=True, editable=False)
    customer = models.ForeignKey(Customer,on_delete=models.SET_NULL,null=True,related_name='tailor_orders',)
    tailor = models.ForeignKey(Tailor,on_delete=models.SET_NULL,null=True,related_name='tailor_orders',)

    # Optional: customer picks fabric & embroidery from tailor's catalog
    fabric = models.ForeignKey(Fabric,on_delete=models.SET_NULL,null=True,blank=True,related_name='tailor_orders',)
    embroidery = models.ForeignKey(Embroidery,on_delete=models.SET_NULL,null=True,blank=True,related_name='tailor_orders',)

    # Dress details
    dress_type = models.CharField(max_length=100)
    dress_description = models.TextField(null=True, blank=True)
    reference_image = models.ImageField(upload_to='tailor_orders/references/',null=True,blank=True,)

    # Measurements snapshot (at time of order)
    measurements = models.JSONField(default=dict, blank=True)
    # e.g. {"chest": 36, "waist": 30, "hip": 38, "shoulder": 14, ...}

    # Fabric details (if customer brings own fabric)
    customer_fabric_description = models.TextField(null=True, blank=True)
    fabric_yards_required = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True,)

    # Pricing
    stitching_charge = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    fabric_charge = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    embroidery_charge = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    additional_charge = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    grand_total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    advance_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    due_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # Status
    status = models.CharField(max_length=20,choices=OrderStatusChoice.choices,default=OrderStatusChoice.PENDING,)
    payment_status = models.CharField(max_length=20,choices=PaymentStatusChoice.choices,default=PaymentStatusChoice.UNPAID,)
    payment_method = models.CharField(max_length=20,choices=PaymentMethodChoice.choices,null=True,blank=True,)
    transaction_id = models.CharField(max_length=100, null=True, blank=True)

    # Delivery
    delivery_address = models.TextField(null=True, blank=True)
    delivery_city = models.CharField(max_length=100, null=True, blank=True)
    promised_delivery_date = models.DateField(null=True, blank=True)
    actual_delivery_date = models.DateField(null=True, blank=True)

    # Tailor's internal note
    tailor_note = models.TextField(null=True, blank=True)

    ordered_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = 'Tailor Order'
        verbose_name_plural = 'Tailor Orders'
        ordering            = ['-ordered_at']
        indexes = [
            models.Index(fields=['customer', 'status']),
            models.Index(fields=['tailor', 'status']),
            models.Index(fields=['order_number']),
            models.Index(fields=['ordered_at']),
            models.Index(fields=['payment_status']),
        ]

    def save(self, *args, **kwargs):
        if not self.order_number:
            import random, string
            self.order_number = 'TO' + ''.join(
                random.choices(string.digits, k=10)
            )
        # Auto-calculate due_amount
        self.due_amount = self.grand_total - self.advance_paid
        super().save(*args, **kwargs)

    def __str__(self):
        return f"TailorOrder #{self.order_number}"


# ─────────────────────────────────────────
#  8. REVIEW
# ─────────────────────────────────────────

class Review(models.Model):
    customer = models.ForeignKey(Customer,on_delete=models.SET_NULL,related_name='reviews', null=True,blank=True,)
    tailor = models.ForeignKey(Tailor,on_delete=models.SET_NULL,related_name='reviews',null=True,blank=True,)
    pre_dress   = models.ForeignKey(PreDress,on_delete=models.CASCADE,related_name='reviews',null=True,blank=True,)

    # Link to which order this review belongs
    pre_dress_order = models.OneToOneField(PreDressOrder,on_delete=models.SET_NULL,null=True,blank=True,related_name='review',)
    tailor_order = models.OneToOneField(TailorOrder,on_delete=models.SET_NULL,null=True,blank=True,related_name='review',)

    rating = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)],)
    title = models.CharField(max_length=200, null=True, blank=True)
    comment = models.TextField(null=True, blank=True)
    image = models.ImageField(upload_to='reviews/',null=True,blank=True,)

    is_verified_purchase = models.BooleanField(default=False)
    is_visible = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = 'Review'
        verbose_name_plural = 'Reviews'
        ordering            = ['-created_at']
        indexes = [
            models.Index(fields=['tailor', 'is_visible']),
            models.Index(fields=['pre_dress', 'is_visible']),
            models.Index(fields=['rating']),
        ]

    def __str__(self):
        target = self.tailor or self.pre_dress
        return f"Review by {self.customer} → {target} [{self.rating}★]"


# ─────────────────────────────────────────
#  9. NOTIFICATION
# ─────────────────────────────────────────

class Notification(models.Model):
    recipient = models.ForeignKey(User,on_delete=models.SET_NULL,related_name='notifications',null=True,blank=True,)
    notification_type = models.CharField(max_length=20,choices=NotificationTypeChoice.choices,default=NotificationTypeChoice.SYSTEM,)
    title = models.CharField(max_length=255)
    message = models.TextField()

    # Generic link to related object (flexible)
    related_object_id = models.UUIDField(null=True, blank=True)
    related_object_type = models.CharField(max_length=50, null=True, blank=True)
    # e.g. "tailor_order", "pre_dress_order", "review"

    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = 'Notification'
        verbose_name_plural = 'Notifications'
        ordering            = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', 'is_read']),
            models.Index(fields=['created_at']),
        ]

    def mark_as_read(self):
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at'])

    def __str__(self):
        return f"Notification → {self.recipient.username} | {self.title}"


# ─────────────────────────────────────────
#  10. CONVERSATION
# ─────────────────────────────────────────

class Conversation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    customer = models.ForeignKey(Customer,on_delete=models.SET_NULL,related_name='conversations',null=True,blank=True,)
    tailor = models.ForeignKey(Tailor,on_delete=models.SET_NULL,related_name='conversations',null=True,blank=True,)

    # Optionally link to a specific order
    related_tailor_order    = models.ForeignKey(TailorOrder,on_delete=models.SET_NULL,null=True,blank=True,related_name='conversations',)
    related_pre_dress_order = models.ForeignKey(PreDressOrder,on_delete=models.SET_NULL,null=True,blank=True,related_name='conversations',)

    last_message_at  = models.DateTimeField(null=True, blank=True)
    last_message_preview = models.CharField(max_length=200, blank=True)

    # Unread count cache
    customer_unread = models.PositiveIntegerField(default=0)
    tailor_unread = models.PositiveIntegerField(default=0)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = 'Conversation'
        verbose_name_plural = 'Conversations'
        unique_together     = ('customer', 'tailor')
        ordering            = ['-last_message_at']
        indexes = [
            models.Index(fields=['customer', 'tailor']),
            models.Index(fields=['last_message_at']),
        ]

    def __str__(self):
        return f"Conversation: {self.customer} ↔ {self.tailor}"


# ─────────────────────────────────────────
#  11. MESSAGE
# ─────────────────────────────────────────

class Message(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation = models.ForeignKey(Conversation,on_delete=models.SET_NULL,related_name='messages',null=True,blank=True,)
    sender = models.ForeignKey(User,on_delete=models.SET_NULL,null=True,related_name='sent_messages',)
    content = models.TextField(blank=True)
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = 'Message'
        verbose_name_plural = 'Messages'
        ordering            = ['sent_at']
        indexes = [
            models.Index(fields=['conversation', 'sent_at']),
            models.Index(fields=['sender', 'is_read']),
        ]

    def __str__(self):
        return f"Message from {self.sender} in {self.conversation.id}"


# ─────────────────────────────────────────
#  12. MESSAGE IMAGE
# ─────────────────────────────────────────

class MessageImage(models.Model):
    message = models.ForeignKey(Message,on_delete=models.CASCADE,related_name='images',)
    image = models.ImageField(upload_to='messages/images/')
    caption = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = 'Message Image'
        verbose_name_plural = 'Message Images'

    def __str__(self):
        return f"Image in Message {self.message.id}"
