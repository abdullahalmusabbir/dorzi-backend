from rest_framework import serializers
from django.contrib.auth.models import User
from django.db import transaction
from .models import *

def is_tailor(user):
    return hasattr(user, 'tailor')

def is_customer(user):
    return hasattr(user, 'customer')
# ─────────────────────────────────────────
#  HELPER — nested user info
# ─────────────────────────────────────────

class BasicUserSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()

    class Meta:
        model  = User
        fields = ['id', 'username', 'email', 'full_name']

    def get_full_name(self, obj):
        return obj.get_full_name() or obj.username


# ─────────────────────────────────────────
#  AUTH — Register
# ─────────────────────────────────────────

class CustomerRegisterSerializer(serializers.ModelSerializer):
    username     = serializers.CharField(write_only=True)
    email        = serializers.EmailField(write_only=True)
    password     = serializers.CharField(write_only=True, min_length=6)
    first_name   = serializers.CharField(write_only=True)
    last_name    = serializers.CharField(write_only=True, required=False, default='')
    phone_number = serializers.CharField()

    class Meta:
        model  = Customer
        fields = [
            'username', 'email', 'password',
            'first_name', 'last_name',
            'phone_number', 'gender', 'date_of_birth',
        ]

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("এই username টি ইতিমধ্যে নেওয়া হয়েছে।")
        return value

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("এই email দিয়ে একটি account আছে।")
        return value

    def validate_phone_number(self, value):
        if Customer.objects.filter(phone_number=value).exists():
            raise serializers.ValidationError("এই phone number টি ইতিমধ্যে registered।")
        return value

    def create(self, validated_data):
        user = User.objects.create_user(
            username   = validated_data['username'],
            email      = validated_data['email'],
            password   = validated_data['password'],
            first_name = validated_data['first_name'],
            last_name  = validated_data.get('last_name', ''),
        )
        customer = Customer.objects.create(
            user         = user,
            phone_number = validated_data['phone_number'],
            gender       = validated_data.get('gender', 'male'),
            date_of_birth= validated_data.get('date_of_birth'),
        )
        return customer


class TailorRegisterSerializer(serializers.ModelSerializer):
    username   = serializers.CharField(write_only=True)
    email      = serializers.EmailField(write_only=True)
    password   = serializers.CharField(write_only=True, min_length=6)
    first_name = serializers.CharField(write_only=True)
    last_name  = serializers.CharField(write_only=True, required=False, default='')
    shop_name  = serializers.CharField(write_only=True, required=True)  
    phone_number = serializers.CharField(write_only=True, required=True)  
    address    = serializers.CharField(write_only=True, required=True)   
    city       = serializers.CharField(write_only=True, required=True)   
    district   = serializers.CharField(write_only=True, required=True) 
    gender     = serializers.CharField(required=False, default='male')

    class Meta:
        model = Tailor
        fields = (
            "username",
            "email",
            "password",
            "first_name",
            "last_name",
            "shop_name",
            "phone_number",
            "address",
            "city",
            "district",
            "gender",
        )

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("এই username টি ইতিমধ্যে নেওয়া হয়েছে।")
        return value

    def validate_phone_number(self, value):
        if Tailor.objects.filter(phone_number=value).exists():
            raise serializers.ValidationError("এই phone number টি Tailor হিসেবে registered।")

        if Customer.objects.filter(phone_number=value).exists():
            raise serializers.ValidationError("এই phone number টি Customer হিসেবে registered।")

        return value  # ← এই লাইন যোগ করো

    def validate_email(self, value): 
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("এই email দিয়ে একটি account আছে।")
        return value

    @transaction.atomic
    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data.pop("username"),
            email=validated_data.pop("email"),
            password=validated_data.pop("password"),
            first_name=validated_data.pop("first_name"),
            last_name=validated_data.pop("last_name", ""),
        )

        # Customer create — phone_number required
        customer = Customer.objects.create(
            user=user,
            phone_number=validated_data.get("phone_number", ""),
        )

        # Tailor create
        tailor = Tailor.objects.create(
            user=user,
            shop_name=validated_data.get("shop_name", ""),
            phone_number=validated_data.get("phone_number", ""),
            address=validated_data.get("address", ""),
            city=validated_data.get("city", ""),
            district=validated_data.get("district", ""),
            gender=validated_data.get("gender", "male"),
        )

        return tailor


# ─────────────────────────────────────────
#  CUSTOMER
# ─────────────────────────────────────────

class CustomerSerializer(serializers.ModelSerializer):
    user      = BasicUserSerializer(read_only=True)
    full_name = serializers.SerializerMethodField()

    class Meta:
        model  = Customer
        fields = [
            'id', 'user', 'full_name',
            'profile_picture', 'phone_number',
            'gender', 'date_of_birth',
            'address', 'city', 'district', 'postal_code',
            'chest', 'waist', 'hip', 'shoulder',
            'sleeve', 'neck', 'inseam', 'height', 'weight',
            'is_verified', 'created_at',
        ]
        read_only_fields = ['id', 'is_verified', 'created_at']

    def get_full_name(self, obj):
        return obj.user.get_full_name() or obj.user.username


class CustomerMeasurementSerializer(serializers.ModelSerializer):
    """শুধু measurement update করার জন্য।"""
    class Meta:
        model  = Customer
        fields = [
            'chest', 'waist', 'hip', 'shoulder',
            'sleeve', 'neck', 'inseam', 'height', 'weight',
        ]


# ─────────────────────────────────────────
#  TAILOR
# ─────────────────────────────────────────

class TailorCardSerializer(serializers.ModelSerializer):
    """
    List page এ tailor card দেখানোর জন্য — হালকা।
    """
    class Meta:
        model  = Tailor
        fields = [
            'id', 'shop_name', 'shop_logo',
            'city', 'district',
            'average_rating', 'total_reviews',
            'total_orders', 'is_verified',
            'is_available', 'experience_years',
            'is_active_shop',
            'created_at',
        ]


class TailorDetailSerializer(serializers.ModelSerializer):
    user = BasicUserSerializer(read_only=True)

    class Meta:
        model  = Tailor
        fields = [
            'id', 'user',
            'shop_name', 'shop_logo', 'shop_banner', 'shop_description',
            'phone_number', 'whatsapp_number',
            'gender', 'address', 'city', 'district', 'postal_code',
            'experience_years', 'specializations',
            'bkash_number', 'nagad_number',
            'average_rating', 'total_reviews',
            'total_orders', 'completed_orders',
            'is_verified', 'is_active_shop', 'is_available',
            'created_at','profile_picture',
        ]
        read_only_fields = [
            'id', 'average_rating', 'total_reviews',
            'total_orders', 'completed_orders',
            'is_verified', 'created_at',
        ]

class TailorMeasurementSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Tailor
        fields = [
            'chest', 'waist', 'hip', 'shoulder',
            'sleeve', 'neck', 'inseam', 'height', 'weight',
        ]
# ─────────────────────────────────────────
#  FABRIC
# ─────────────────────────────────────────

class FabricSerializer(serializers.ModelSerializer):
    tailor_name = serializers.CharField(source='tailor.shop_name', read_only=True)

    class Meta:
        model  = Fabric
        fields = [
            'id', 'tailor', 'tailor_name',
            'name', 'fabric_type', 'description',
            'color', 'pattern', 'image',
            'price_per_yard', 'stock_yards', 'is_available',
            'created_at',
        ]
        read_only_fields = ['id', 'tailor', 'created_at']

    def validate_price_per_yard(self, value):
        if value <= 0:
            raise serializers.ValidationError("Price অবশ্যই 0 এর বেশি হতে হবে।")
        return value

    def validate_stock_yards(self, value):
        if value < 0:
            raise serializers.ValidationError("Stock negative হতে পারবে না।")
        return value


# ─────────────────────────────────────────
#  EMBROIDERY
# ─────────────────────────────────────────

class EmbroiderySerializer(serializers.ModelSerializer):
    tailor_name = serializers.CharField(source='tailor.shop_name', read_only=True)

    class Meta:
        model  = Embroidery
        fields = [
            'id', 'tailor', 'tailor_name',
            'name', 'embroidery_type', 'description',
            'sample_image', 'price', 'extra_days',
            'is_available', 'created_at',
        ]
        read_only_fields = ['id', 'tailor', 'created_at']

    def validate_price(self, value):
        if value < 0:
            raise serializers.ValidationError("Price negative হতে পারবে না।")
        return value


# ─────────────────────────────────────────
#  PRE-DRESS
# ─────────────────────────────────────────

class PreDressImageSerializer(serializers.ModelSerializer):
    class Meta:
        model  = PreDressImage
        fields = ['id', 'image', 'is_primary', 'order']


class PreDressCardSerializer(serializers.ModelSerializer):
    primary_image = serializers.SerializerMethodField()
    tailor_name   = serializers.CharField(source='tailor.shop_name', read_only=True)
    effective_price = serializers.DecimalField(
        max_digits=10, decimal_places=2, read_only=True
    )
    tailor_id = serializers.IntegerField(source='tailor.id', read_only=True)  # <-- ADD THIS LINE

    class Meta:
        model  = PreDress
        fields = [
            'id', 'tailor_name', 'title',
            'category', 'primary_image',
            'price', 'discount_price', 'effective_price',
            'average_rating', 'total_reviews', 'total_sold',
            'is_featured', 'delivery_days', 'is_active',
            'tailor_id',   # <-- ADD THIS LINE
        ]

    def get_primary_image(self, obj):
        img = obj.images.filter(is_primary=True).first() \
              or obj.images.first()
        if img:
            request = self.context.get('request')
            return request.build_absolute_uri(img.image.url) if request else img.image.url
        return None


class PreDressDetailSerializer(serializers.ModelSerializer):
    """
    Single dress detail page।
    """
    images      = PreDressImageSerializer(many=True, read_only=True)
    fabric      = FabricSerializer(read_only=True)
    embroidery  = EmbroiderySerializer(read_only=True)
    tailor      = TailorCardSerializer(read_only=True)
    effective_price = serializers.DecimalField(
        max_digits=10, decimal_places=2, read_only=True
    )

    # Write এর জন্য FK id নেওয়া
    fabric_id     = serializers.PrimaryKeyRelatedField(
        queryset=Fabric.objects.filter(is_available=True),
        source='fabric', write_only=True, required=False, allow_null=True,
    )
    embroidery_id = serializers.PrimaryKeyRelatedField(
        queryset=Embroidery.objects.filter(is_available=True),
        source='embroidery', write_only=True, required=False, allow_null=True,
    )

    class Meta:
        model  = PreDress
        fields = [
            'id', 'tailor', 'title', 'description',
            'category', 'sizes_available', 'colors_available',
            'fabric', 'fabric_id',
            'embroidery', 'embroidery_id',
            'price', 'discount_price', 'effective_price',
            'stock_quantity', 'delivery_days', 'tags',
            'images', 'is_active', 'is_featured',
            'average_rating', 'total_reviews', 'total_sold',
            'created_at',
        ]
        read_only_fields = [
            'id', 'tailor', 'average_rating',
            'total_reviews', 'total_sold', 'created_at',
        ]

    def validate(self, data):
        price    = data.get('price', 0)
        dis      = data.get('discount_price')
        if dis and dis >= price:
            raise serializers.ValidationError(
                {"discount_price": "Discount price অবশ্যই actual price এর কম হতে হবে।"}
            )
        return data


# ─────────────────────────────────────────
#  PRE-DRESS ORDER
# ─────────────────────────────────────────

class PreDressOrderCreateSerializer(serializers.ModelSerializer):
    """Customer যখন order দেয়।"""

    class Meta:
        model  = PreDressOrder
        fields = [
            'pre_dress', 'quantity',
            'selected_size', 'selected_color', 'special_note',
            'payment_method',
            'delivery_address', 'delivery_city',
        ]

    def validate_quantity(self, value):
        if value < 1:
            raise serializers.ValidationError("Quantity অন্তত 1 হতে হবে।")
        return value

    def validate(self, data):
        pre_dress = data.get('pre_dress')
        quantity  = data.get('quantity', 1)

        if not pre_dress.is_active:
            raise serializers.ValidationError("এই dress টি এখন available নেই।")

        if pre_dress.stock_quantity < quantity:
            raise serializers.ValidationError(
                f"Stock এ মাত্র {pre_dress.stock_quantity} টি আছে।"
            )
        return data

    def create(self, validated_data):
        user = self.context['request'].user
        if is_customer(user):
            customer = user.customer
        elif is_tailor(user):
            customer, _ = Customer.objects.get_or_create(
                user=user,
                defaults={'phone_number': ''}
            )
        else:
            raise serializers.ValidationError("Only customers or tailors can place orders")
        
        # ── FIX: pop pre_dress before unpacking validated_data ──
        pre_dress = validated_data.pop('pre_dress')
        quantity  = validated_data.get('quantity', 1)
        unit_price   = pre_dress.effective_price
        total_price  = unit_price * quantity
        grand_total  = total_price

        order = PreDressOrder.objects.create(
            customer         = customer,
            tailor           = pre_dress.tailor,
            pre_dress        = pre_dress,
            unit_price       = unit_price,
            total_price      = total_price,
            grand_total      = grand_total,
            **validated_data,
        )
        return order


class PreDressOrderSerializer(serializers.ModelSerializer):
    """Order list & detail দেখার জন্য।"""
    customer_name = serializers.CharField(
        source='customer.user.get_full_name', read_only=True
    )
    tailor_name   = serializers.CharField(
        source='tailor.shop_name', read_only=True
    )
    dress_title   = serializers.CharField(
        source='pre_dress.title', read_only=True
    )

    class Meta:
        model  = PreDressOrder
        fields = [
            'id', 'order_number',
            'customer_name', 'tailor_name', 'dress_title',
            'quantity', 'selected_size', 'selected_color',
            'special_note',
            'unit_price', 'total_price',
            'discount_amount', 'delivery_charge', 'grand_total',
            'status', 'payment_status', 'payment_method',
            'transaction_id',
            'delivery_address', 'delivery_city',
            'estimated_delivery_date', 'actual_delivery_date',
            'ordered_at', 'updated_at',
        ]
        read_only_fields = fields  # list এ শুধু read


class PreDressOrderStatusUpdateSerializer(serializers.ModelSerializer):
    """Tailor order status update করবে।"""
    class Meta:
        model  = PreDressOrder
        fields = ['status', 'payment_status', 'transaction_id', 'actual_delivery_date']


# ─────────────────────────────────────────
#  TAILOR ORDER
# ─────────────────────────────────────────

class TailorOrderCreateSerializer(serializers.ModelSerializer):
    """Customer custom order দেওয়ার সময়।"""

    class Meta:
        model  = TailorOrder
        fields = [
            'tailor',
            'fabric', 'embroidery',
            'dress_type', 'dress_description', 'reference_image',
            'measurements',
            'customer_fabric_description', 'fabric_yards_required',
            'delivery_address', 'delivery_city',
            'payment_method',
        ]

    def validate_measurements(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError("Measurements অবশ্যই JSON object হতে হবে।")
        return value

    def create(self, validated_data):
        user = self.context['request'].user
        if is_customer(user):
            customer = user.customer
        elif is_tailor(user):
            customer, _ = Customer.objects.get_or_create(
                user=user,
                defaults={'phone_number': ''}
            )
        else:
            raise serializers.ValidationError("Only customers or tailors can place orders")
        
        order = TailorOrder.objects.create(
            customer=customer,
            **validated_data,
        )
        return order


class TailorOrderSerializer(serializers.ModelSerializer):
    """Order detail দেখার জন্য।"""
    customer_name  = serializers.CharField(
        source='customer.user.get_full_name', read_only=True
    )
    tailor_name    = serializers.CharField(
        source='tailor.shop_name', read_only=True
    )
    fabric_name    = serializers.CharField(
        source='fabric.name', read_only=True
    )
    embroidery_name = serializers.CharField(
        source='embroidery.name', read_only=True
    )

    class Meta:
        model  = TailorOrder
        fields = [
            'id', 'order_number',
            'customer_name', 'tailor_name',
            'fabric_name', 'embroidery_name',
            'dress_type', 'dress_description', 'reference_image',
            'measurements',
            'customer_fabric_description', 'fabric_yards_required',
            'stitching_charge', 'fabric_charge',
            'embroidery_charge', 'additional_charge',
            'discount_amount', 'grand_total',
            'advance_paid', 'due_amount',
            'status', 'payment_status', 'payment_method',
            'transaction_id',
            'delivery_address', 'delivery_city',
            'promised_delivery_date', 'actual_delivery_date',
            'tailor_note',
            'ordered_at', 'updated_at',
        ]
        read_only_fields = fields


class TailorOrderPricingSerializer(serializers.ModelSerializer):
    """Tailor pricing set করবে।"""
    class Meta:
        model  = TailorOrder
        fields = [
            'stitching_charge', 'fabric_charge',
            'embroidery_charge', 'additional_charge',
            'discount_amount', 'grand_total',
            'advance_paid',
            'promised_delivery_date',
            'tailor_note', 'status',
        ]


# ─────────────────────────────────────────
#  REVIEW
# ─────────────────────────────────────────

class ReviewSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(
        source='customer.user.get_full_name', read_only=True
    )
    customer_pic  = serializers.ImageField(
        source='customer.profile_picture', read_only=True
    )

    class Meta:
        model  = Review
        fields = [
            'id', 'customer_name', 'customer_pic',
            'tailor', 'pre_dress',
            'pre_dress_order', 'tailor_order',
            'rating', 'title', 'comment', 'image',
            'is_verified_purchase',
            'created_at',
        ]
        read_only_fields = ['id', 'is_verified_purchase', 'created_at']

    def validate_rating(self, value):
        if not (1 <= value <= 5):
            raise serializers.ValidationError("Rating 1 থেকে 5 এর মধ্যে হতে হবে।")
        return value

    def validate(self, data):
        # tailor অথবা pre_dress যেকোনো একটা লাগবে
        if not data.get('tailor') and not data.get('pre_dress'):
            raise serializers.ValidationError(
                "Review দিতে হলে tailor অথবা pre_dress দিতে হবে।"
            )
        return data

    def create(self, validated_data):
        customer = self.context['request'].user.customer
        return Review.objects.create(customer=customer, **validated_data)


# ─────────────────────────────────────────
#  NOTIFICATION
# ─────────────────────────────────────────

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Notification
        fields = [
            'id', 'notification_type',
            'title', 'message',
            'related_object_id', 'related_object_type',
            'is_read', 'read_at', 'created_at',
        ]
        read_only_fields = fields

class NotificationMarkReadSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Notification
        fields = ['is_read']


# ─────────────────────────────────────────
#  CONVERSATION & MESSAGE
# ─────────────────────────────────────────

class MessageImageSerializer(serializers.ModelSerializer):
    class Meta:
        model  = MessageImage
        fields = ['id', 'image', 'caption', 'created_at']


class MessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.CharField(
        source='sender.get_full_name', read_only=True
    )
    images = MessageImageSerializer(many=True, read_only=True)
    # Image upload এর জন্য write_only list
    uploaded_images = serializers.ListField(
        child=serializers.ImageField(),
        write_only=True, required=False,
    )

    class Meta:
        model  = Message
        fields = [
            'id', 'conversation',
            'sender_name', 'content',
            'images', 'uploaded_images',
            'is_read', 'read_at', 'sent_at',
        ]
        read_only_fields = ['id', 'conversation', 'is_read', 'read_at', 'sent_at']

    def create(self, validated_data):
        images_data = validated_data.pop('uploaded_images', [])
        message     = Message.objects.create(**validated_data)

        for img in images_data:
            MessageImage.objects.create(message=message, image=img)

        return message


class ConversationSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(
        source='customer.user.get_full_name', read_only=True
    )
    tailor_name   = serializers.CharField(
        source='tailor.shop_name', read_only=True
    )
    customer_pic  = serializers.ImageField(
        source='customer.profile_picture', read_only=True
    )
    tailor_pic    = serializers.ImageField(
        source='tailor.shop_logo', read_only=True
    )
    # Last message preview already in model field
    messages      = MessageSerializer(many=True, read_only=True)

    class Meta:
        model  = Conversation
        fields = [
            'id',
            'customer_name', 'customer_pic',
            'tailor_name', 'tailor_pic',
            'related_tailor_order', 'related_pre_dress_order',
            'last_message_at', 'last_message_preview',
            'customer_unread', 'tailor_unread',
            'is_active', 'created_at',
            'messages',
        ]
        read_only_fields = fields


class ConversationListSerializer(serializers.ModelSerializer):
    """Inbox list এ শুধু conversation card।"""
    customer_name = serializers.CharField(
        source='customer.user.get_full_name', read_only=True
    )
    tailor_name   = serializers.CharField(
        source='tailor.shop_name', read_only=True
    )

    class Meta:
        model  = Conversation
        fields = [
            'id', 'customer_name', 'tailor_name',
            'last_message_at', 'last_message_preview',
            'customer_unread', 'tailor_unread',
        ]