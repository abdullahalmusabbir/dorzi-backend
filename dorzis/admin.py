from django.contrib import admin
from django.utils.html import format_html
from .models import *

# ─────────────────────────────────────────
#  CUSTOMER
# ─────────────────────────────────────────

@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display  = ['get_name', 'phone_number', 'city', 'is_verified', 'created_at']
    list_filter   = ['is_verified', 'gender', 'city']
    search_fields = ['user__username', 'user__email', 'phone_number', 'city']
    readonly_fields = ['created_at', 'updated_at']

    fieldsets = (
        ('Account', {
            'fields': ('user', 'profile_picture', 'is_verified')
        }),
        ('Personal Info', {
            'fields': ('phone_number', 'gender', 'date_of_birth')
        }),
        ('Address', {
            'fields': ('address', 'city', 'district', 'postal_code')
        }),
        ('Measurements (cm)', {
            'classes': ('collapse',),
            'fields': (
                ('chest', 'waist', 'hip'),
                ('shoulder', 'sleeve', 'neck'),
                ('inseam', 'height', 'weight'),
            ),
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )

    @admin.display(description='Name')
    def get_name(self, obj):
        return obj.user.get_full_name() or obj.user.username


# ─────────────────────────────────────────
#  TAILOR
# ─────────────────────────────────────────

@admin.register(Tailor)
class TailorAdmin(admin.ModelAdmin):
    list_display  = [
        'shop_name', 'get_logo', 'phone_number',
        'city', 'average_rating', 'is_verified',
        'is_active_shop', 'created_at'
    ]
    list_filter   = ['is_verified', 'is_active_shop', 'is_available', 'city', 'district']
    search_fields = ['shop_name', 'user__username', 'phone_number', 'city']
    readonly_fields = [
        'average_rating', 'total_reviews',
        'total_orders', 'completed_orders',
        'created_at', 'updated_at',
    ]

    fieldsets = (
        ('Account', {
            'fields': ('user', 'is_verified', 'is_active_shop', 'is_available')
        }),
        ('Shop Info', {
            'fields': (
                'shop_name', 'shop_logo', 'shop_banner',
                'shop_description', 'specializations',
            )
        }),
        ('Contact', {
            'fields': ('phone_number', 'whatsapp_number', 'gender')
        }),
        ('Address', {
            'fields': ('address', 'city', 'district', 'postal_code')
        }),
        ('Experience', {
            'fields': ('experience_years',)
        }),
        ('Payment Info', {
            'classes': ('collapse',),
            'fields': ('bkash_number', 'nagad_number', 'bank_account')
        }),
        ('Business Docs', {
            'classes': ('collapse',),
            'fields': ('nid_number', 'trade_license')
        }),
        ('Stats (auto)', {
            'fields': (
                'average_rating', 'total_reviews',
                'total_orders', 'completed_orders',
            )
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )


    @admin.display(description='Logo')
    def get_logo(self, obj):
        if obj.shop_logo:
            return format_html(
                '<img src="{}" width="40" height="40" style="border-radius:50%"/>',
                obj.shop_logo.url
            )
        return '—'


# ─────────────────────────────────────────
#  FABRIC
# ─────────────────────────────────────────

@admin.register(Fabric)
class FabricAdmin(admin.ModelAdmin):
    list_display  = [
        'name', 'tailor', 'fabric_type',
        'price_per_yard', 'stock_yards', 'is_available'
    ]
    list_filter   = ['fabric_type', 'is_available']
    search_fields = ['name', 'tailor__shop_name']
    list_editable = ['is_available', 'stock_yards']


# ─────────────────────────────────────────
#  EMBROIDERY
# ─────────────────────────────────────────

@admin.register(Embroidery)
class EmbroideryAdmin(admin.ModelAdmin):
    list_display  = [
        'name', 'tailor', 'embroidery_type',
        'price', 'extra_days', 'is_available'
    ]
    list_filter   = ['embroidery_type', 'is_available']
    search_fields = ['name', 'tailor__shop_name']
    list_editable = ['is_available']


# ─────────────────────────────────────────
#  PRE-DRESS
# ─────────────────────────────────────────

class PreDressImageInline(admin.TabularInline):
    model  = PreDressImage
    extra  = 1
    fields = ['image', 'is_primary', 'order']


@admin.register(PreDress)
class PreDressAdmin(admin.ModelAdmin):
    list_display  = [
        'title', 'tailor', 'category',
        'price', 'discount_price', 'stock_quantity',
        'average_rating', 'total_sold',
        'is_active', 'is_featured',
    ]
    list_filter   = ['category', 'is_active', 'is_featured']
    search_fields = ['title', 'tailor__shop_name', 'tags']
    list_editable = ['is_active', 'is_featured']
    readonly_fields = ['average_rating', 'total_reviews', 'total_sold', 'created_at', 'updated_at']
    inlines       = [PreDressImageInline]

    fieldsets = (
        ('Basic Info', {
            'fields': ('tailor', 'title', 'description', 'category', 'tags')
        }),
        ('Options', {
            'fields': ('sizes_available', 'colors_available', 'fabric', 'embroidery')
        }),
        ('Pricing & Stock', {
            'fields': ('price', 'discount_price', 'stock_quantity', 'delivery_days')
        }),
        ('Visibility', {
            'fields': ('is_active', 'is_featured')
        }),
        ('Stats (auto)', {
            'fields': ('average_rating', 'total_reviews', 'total_sold')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )


# ─────────────────────────────────────────
#  PRE-DRESS ORDER
# ─────────────────────────────────────────

@admin.register(PreDressOrder)
class PreDressOrderAdmin(admin.ModelAdmin):
    list_display  = [
        'order_number', 'get_customer', 'get_tailor',
        'get_dress', 'quantity', 'grand_total',
        'status', 'payment_status', 'ordered_at',
    ]
    list_filter   = ['status', 'payment_status', 'payment_method']
    search_fields = ['order_number', 'customer__user__username', 'tailor__shop_name']
    readonly_fields = [
        'order_number', 'unit_price', 'total_price',
        'grand_total', 'ordered_at', 'updated_at',
    ]

    @admin.display(description='Customer')
    def get_customer(self, obj):
        return obj.customer.user.get_full_name() if obj.customer else '—'

    @admin.display(description='Tailor')
    def get_tailor(self, obj):
        return obj.tailor.shop_name if obj.tailor else '—'

    @admin.display(description='Dress')
    def get_dress(self, obj):
        return obj.pre_dress.title if obj.pre_dress else '—'


# ─────────────────────────────────────────
#  TAILOR ORDER
# ─────────────────────────────────────────

@admin.register(TailorOrder)
class TailorOrderAdmin(admin.ModelAdmin):
    list_display  = [
        'order_number', 'get_customer', 'get_tailor',
        'dress_type', 'grand_total', 'due_amount',
        'status', 'payment_status', 'ordered_at',
    ]
    list_filter   = ['status', 'payment_status', 'payment_method']
    search_fields = ['order_number', 'customer__user__username', 'tailor__shop_name', 'dress_type']
    readonly_fields = ['order_number', 'due_amount', 'ordered_at', 'updated_at']

    fieldsets = (
        ('Order Info', {
            'fields': ('order_number', 'customer', 'tailor', 'dress_type', 'dress_description')
        }),
        ('Fabric & Embroidery', {
            'fields': ('fabric', 'embroidery', 'customer_fabric_description', 'fabric_yards_required')
        }),
        ('Measurements', {
            'fields': ('measurements',)
        }),
        ('Pricing', {
            'fields': (
                'stitching_charge', 'fabric_charge',
                'embroidery_charge', 'additional_charge',
                'discount_amount', 'grand_total',
                'advance_paid', 'due_amount',
            )
        }),
        ('Payment', {
            'fields': ('payment_status', 'payment_method', 'transaction_id')
        }),
        ('Status & Delivery', {
            'fields': (
                'status', 'delivery_address', 'delivery_city',
                'promised_delivery_date', 'actual_delivery_date',
                'tailor_note', 'reference_image',
            )
        }),
        ('Timestamps', {
            'fields': ('ordered_at', 'updated_at')
        }),
    )

    @admin.display(description='Customer')
    def get_customer(self, obj):
        return obj.customer.user.get_full_name() if obj.customer else '—'

    @admin.display(description='Tailor')
    def get_tailor(self, obj):
        return obj.tailor.shop_name if obj.tailor else '—'


# ─────────────────────────────────────────
#  REVIEW
# ─────────────────────────────────────────

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display  = [
        'get_customer', 'get_target',
        'rating', 'is_verified_purchase',
        'is_visible', 'created_at',
    ]
    list_filter   = ['rating', 'is_verified_purchase', 'is_visible']
    search_fields = ['customer__user__username', 'tailor__shop_name', 'comment']
    list_editable = ['is_visible']

    @admin.display(description='Customer')
    def get_customer(self, obj):
        return obj.customer.user.get_full_name()

    @admin.display(description='Reviewed')
    def get_target(self, obj):
        if obj.tailor:
            return f"Tailor: {obj.tailor.shop_name}"
        if obj.pre_dress:
            return f"Dress: {obj.pre_dress.title}"
        return '—'


# ─────────────────────────────────────────
#  NOTIFICATION
# ─────────────────────────────────────────

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display  = [
        'recipient', 'notification_type',
        'title', 'is_read', 'created_at'
    ]
    list_filter   = ['notification_type', 'is_read']
    search_fields = ['recipient__username', 'title', 'message']
    readonly_fields = ['created_at', 'read_at']


# ─────────────────────────────────────────
#  CONVERSATION & MESSAGE
# ─────────────────────────────────────────

class MessageInline(admin.TabularInline):
    model   = Message
    extra   = 0
    fields  = ['sender', 'content', 'is_read', 'sent_at']
    readonly_fields = ['sent_at']


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display  = [
        'id', 'get_customer', 'get_tailor',
        'last_message_at', 'customer_unread', 'tailor_unread',
        'is_active',
    ]
    list_filter   = ['is_active']
    search_fields = ['customer__user__username', 'tailor__shop_name']
    readonly_fields = ['created_at', 'last_message_at']
    inlines       = [MessageInline]

    @admin.display(description='Customer')
    def get_customer(self, obj):
        return obj.customer.user.get_full_name()

    @admin.display(description='Tailor')
    def get_tailor(self, obj):
        return obj.tailor.shop_name


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display  = ['id', 'get_conversation', 'sender', 'is_read', 'sent_at']
    list_filter   = ['is_read']
    search_fields = ['sender__username', 'content']
    readonly_fields = ['sent_at', 'read_at']

    @admin.display(description='Conversation')
    def get_conversation(self, obj):
        return f"{obj.conversation.customer} ↔ {obj.conversation.tailor}"