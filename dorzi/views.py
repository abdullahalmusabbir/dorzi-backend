# dorzis/views.py

from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils import timezone
from django.db.models import Q
from django.conf import settings

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView
from rest_framework_simplejwt.exceptions import TokenError

from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

from dorzis.models import *
from dorzis.serializers import *


# ─────────────────────────────────────────
#  HELPER FUNCTIONS
# ─────────────────────────────────────────

def get_tokens(user):
    refresh = RefreshToken.for_user(user)
    return {
        'refresh': str(refresh),
        'access' : str(refresh.access_token),
    }

def success(data=None, msg="Success", status_code=status.HTTP_200_OK):
    return Response({'success': True, 'message': msg, 'data': data}, status=status_code)

def error(msg="Something went wrong", status_code=status.HTTP_400_BAD_REQUEST, errors=None):
    return Response({'success': False, 'message': msg, 'errors': errors}, status=status_code)

def is_tailor(user):
    return hasattr(user, 'tailor')

def is_customer(user):
    return hasattr(user, 'customer')


# ─────────────────────────────────────────
#  AUTH — REGISTER
# ─────────────────────────────────────────

class CustomerRegisterView(APIView):
    permission_classes = [AllowAny]
    parser_classes     = [MultiPartParser, FormParser, JSONParser]

    def post(self, request):
        serializer = CustomerRegisterSerializer(data=request.data)
        if not serializer.is_valid():
            return error("Registration failed", errors=serializer.errors)

        customer = serializer.save()
        tokens   = get_tokens(customer.user)
        data     = CustomerSerializer(customer, context={'request': request}).data

        return success(
            data       = {'user': data, 'tokens': tokens},
            msg        = "Registration successful",
            status_code= status.HTTP_201_CREATED,
        )

class TailorRegisterView(APIView):
    permission_classes = [AllowAny]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def post(self, request):
        serializer = TailorRegisterSerializer(data=request.data)

        if not serializer.is_valid():
            return error("Registration failed", errors=serializer.errors)

        tailor = serializer.save()
        tokens = get_tokens(tailor.user)
        data = TailorDetailSerializer(
            tailor,
            context={"request": request}
        ).data

        return success(
            data={
                "user": data,
                "tokens": tokens,
            },
            msg="Registration successful",
            status_code=status.HTTP_201_CREATED,
        )

# ─────────────────────────────────────────
#  AUTH — LOGIN / LOGOUT
# ─────────────────────────────────────────

class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        username = request.data.get('username', '').strip()
        password = request.data.get('password', '').strip()

        if not username or not password:
            return error("Username and password required")

        # email দিয়েও login হবে
        user = User.objects.filter(
            Q(username=username) | Q(email=username)
        ).first()

        if not user or not user.check_password(password):
            return error("Invalid credentials", status_code=status.HTTP_401_UNAUTHORIZED)

        if not user.is_active:
            return error("Account is disabled", status_code=status.HTTP_403_FORBIDDEN)

        tokens = get_tokens(user)

        # user type বের করা — tailor আগে, customer পরে
        if is_tailor(user):
            profile = TailorDetailSerializer(user.tailor, context={'request': request}).data
            role    = 'tailor'
        elif is_customer(user):
            profile = CustomerSerializer(user.customer, context={'request': request}).data
            role    = 'customer'
        else:
            profile = None
            role    = 'unknown'

        return success(data={
            'tokens': tokens,
            'role'  : role,
            'profile': profile,
        })

class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh_token = request.data.get('refresh')
        if not refresh_token:
            # No token provided — still succeed, frontend will clear local state
            return success(msg="Logged out successfully")

        try:
            token = RefreshToken(refresh_token)
            # token.blacklist()  # enable if you want to blacklist
            return success(msg="Logged out successfully")
        except TokenError:
            # Token already invalid/expired — treat as success anyway
            return success(msg="Logged out successfully")

# ─────────────────────────────────────────
#  AUTH — FORGOT / RESET PASSWORD
# ─────────────────────────────────────────

class ForgotPasswordView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get('email', '').strip()
        if not email:
            return error("Email is required")

        user = User.objects.filter(email=email).first()
        # Security: always return success (email enumeration রোধ)
        if user:
            uid   = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            reset_link = f"{settings.FRONTEND_URL}/reset-password/{uid}/{token}/"

            send_mail(
                subject    = "DorZI — Password Reset",
                message    = f"Click the link to reset your password:\n{reset_link}",
                from_email = settings.DEFAULT_FROM_EMAIL,
                recipient_list = [email],
                fail_silently  = True,
            )

        return success(msg="If this email exists, a reset link has been sent")

class ResetPasswordView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, uid, token):
        new_password = request.data.get('new_password', '').strip()
        if not new_password or len(new_password) < 6:
            return error("Password must be at least 6 characters")

        try:
            pk   = force_str(urlsafe_base64_decode(uid))
            user = User.objects.get(pk=pk)
        except (User.DoesNotExist, ValueError):
            return error("Invalid reset link", status_code=status.HTTP_400_BAD_REQUEST)

        if not default_token_generator.check_token(user, token):
            return error("Reset link expired or invalid")

        user.set_password(new_password)
        user.save()
        return success(msg="Password reset successful")

class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        old_password = request.data.get('old_password', '')
        new_password = request.data.get('new_password', '')

        if not request.user.check_password(old_password):
            return error("Old password is incorrect")

        if len(new_password) < 6:
            return error("New password must be at least 6 characters")

        request.user.set_password(new_password)
        request.user.save()
        return success(msg="Password changed successfully")

# ─────────────────────────────────────────
#  AUTH — GOOGLE LOGIN
# ─────────────────────────────────────────
class GoogleLoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        google_token = request.data.get('token')
        role         = request.data.get('role', 'customer')  # 'customer' or 'tailor'

        if not google_token:
            return error("Google token required")

        try:
            id_info = id_token.verify_oauth2_token(
                google_token,
                google_requests.Request(),
                settings.GOOGLE_CLIENT_ID,
            )
        except ValueError:
            return error("Invalid Google token", status_code=status.HTTP_401_UNAUTHORIZED)

        email      = id_info.get('email')
        first_name = id_info.get('given_name', '')
        last_name  = id_info.get('family_name', '')
        google_id  = id_info.get('sub')

        if not email:
            return error("Could not fetch email from Google")

        # User আছে কিনা চেক করো
        user, created = User.objects.get_or_create(
            email    = email,
            defaults = {
                'username'  : email.split('@')[0] + '_' + google_id[:6],
                'first_name': first_name,
                'last_name' : last_name,
            }
        )

        # Profile setup যদি নতুন user হয়
        if created:
            user.set_unusable_password()
            user.save()

            if role == 'tailor':
                Tailor.objects.get_or_create(
                    user      = user,
                    defaults  = {
                        'shop_name'   : f"{first_name}'s Shop",
                        'phone_number': '',
                        'address'     : '',
                        'city'        : '',
                        'district'    : '',
                    }
                )
            else:
                Customer.objects.get_or_create(
                    user     = user,
                    defaults = {'phone_number': ''},
                )

        tokens = get_tokens(user)

        if is_customer(user):
            profile = CustomerSerializer(user.customer, context={'request': request}).data
            user_role = 'customer'
        elif is_tailor(user):
            profile = TailorDetailSerializer(user.tailor, context={'request': request}).data
            user_role = 'tailor'
        else:
            profile   = None
            user_role = 'unknown'

        return success(data={
            'tokens' : tokens,
            'role'   : user_role,
            'profile': profile,
            'created': created,
        })

# ─────────────────────────────────────────
#  CUSTOMER PROFILE
# ─────────────────────────────────────────
class CustomerProfileView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes     = [MultiPartParser, FormParser, JSONParser]

    def get(self, request):
        if not is_customer(request.user):
            return error("Not a customer", status_code=status.HTTP_403_FORBIDDEN)
        data = CustomerSerializer(request.user.customer, context={'request': request}).data
        return success(data=data)

    def patch(self, request):
        if not is_customer(request.user):
            return error("Not a customer", status_code=status.HTTP_403_FORBIDDEN)
        serializer = CustomerSerializer(
            request.user.customer,
            data    = request.data,
            partial = True,
            context = {'request': request},
        )
        if not serializer.is_valid():
            return error("Update failed", errors=serializer.errors)
        serializer.save()
        return success(data=serializer.data, msg="Profile updated")

class CustomerMeasurementView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not is_customer(request.user):
            return error("Not a customer", status_code=status.HTTP_403_FORBIDDEN)
        data = CustomerMeasurementSerializer(request.user.customer).data
        return success(data=data)

    def patch(self, request):
        if not is_customer(request.user):
            return error("Not a customer", status_code=status.HTTP_403_FORBIDDEN)
        serializer = CustomerMeasurementSerializer(
            request.user.customer,
            data    = request.data,
            partial = True,
        )
        if not serializer.is_valid():
            return error("Update failed", errors=serializer.errors)
        serializer.save()
        return success(data=serializer.data, msg="Measurements updated")

# ─────────────────────────────────────────
#  TAILOR PROFILE
# ─────────────────────────────────────────
class TailorListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        qs = Tailor.objects.filter(
            is_active_shop=True, is_verified=True
        ).select_related('user').order_by('-is_active_shop', '-created_at', '-id')

        # Filter
        city     = request.query_params.get('city')
        district = request.query_params.get('district')
        search   = request.query_params.get('search')

        if city:
            qs = qs.filter(city__icontains=city)
        if district:
            qs = qs.filter(district__icontains=district)
        if search:
            qs = qs.filter(
                Q(shop_name__icontains=search) |
                Q(specializations__icontains=search)
            )

        data = TailorCardSerializer(qs, many=True, context={'request': request}).data
        return success(data=data)

class TailorDetailView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, pk):
        tailor = Tailor.objects.filter(pk=pk).select_related('user').first()
        if not tailor:
            return error("Tailor not found", status_code=status.HTTP_404_NOT_FOUND)
        data = TailorDetailSerializer(tailor, context={'request': request}).data
        return success(data=data)

class MyTailorProfileView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes     = [MultiPartParser, FormParser, JSONParser]

    def get(self, request):
        if not is_tailor(request.user):
            return error("Not a tailor", status_code=status.HTTP_403_FORBIDDEN)
        data = TailorDetailSerializer(request.user.tailor, context={'request': request}).data
        return success(data=data)

    def patch(self, request):
        if not is_tailor(request.user):
            return error("Not a tailor", status_code=status.HTTP_403_FORBIDDEN)
        serializer = TailorDetailSerializer(
            request.user.tailor,
            data    = request.data,
            partial = True,
            context = {'request': request},
        )
        if not serializer.is_valid():
            return error("Update failed", errors=serializer.errors)
        serializer.save()
        return success(data=serializer.data, msg="Profile updated")

class TailorMeasurementView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not is_tailor(request.user):
            return error("Not a tailor", status_code=status.HTTP_403_FORBIDDEN)
        data = TailorMeasurementSerializer(request.user.tailor).data
        return success(data=data)

    def patch(self, request):
        if not is_tailor(request.user):
            return error("Not a tailor", status_code=status.HTTP_403_FORBIDDEN)
        serializer = TailorMeasurementSerializer(
            request.user.tailor,
            data    = request.data,
            partial = True,
        )
        if not serializer.is_valid():
            return error("Update failed", errors=serializer.errors)
        serializer.save()
        return success(data=serializer.data, msg="Measurements updated")
    
# ─────────────────────────────────────────
#  FABRIC
# ─────────────────────────────────────────
class FabricListCreateView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes     = [MultiPartParser, FormParser, JSONParser]

    def get(self, request):
        tailor_id = request.query_params.get('tailor_id')

        if tailor_id:
            qs = Fabric.objects.filter(
                tailor_id=tailor_id, is_available=True
            ).select_related('tailor')
        elif is_tailor(request.user):
            qs = Fabric.objects.filter(
                tailor=request.user.tailor
            ).select_related('tailor')
        else:
            qs = Fabric.objects.filter(is_available=True).select_related('tailor')

        data = FabricSerializer(qs, many=True, context={'request': request}).data
        return success(data=data)

    def post(self, request):
        if not is_tailor(request.user):
            return error("Only tailors can add fabrics", status_code=status.HTTP_403_FORBIDDEN)

        serializer = FabricSerializer(data=request.data, context={'request': request})
        if not serializer.is_valid():
            return error("Failed to add fabric", errors=serializer.errors)

        serializer.save(tailor=request.user.tailor)
        return success(data=serializer.data, msg="Fabric added", status_code=status.HTTP_201_CREATED)

class FabricDetailView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes     = [MultiPartParser, FormParser, JSONParser]

    def get_object(self, pk):
        return Fabric.objects.filter(pk=pk).select_related('tailor').first()

    def get(self, request, pk):
        fabric = self.get_object(pk)
        if not fabric:
            return error("Fabric not found", status_code=status.HTTP_404_NOT_FOUND)
        return success(data=FabricSerializer(fabric, context={'request': request}).data)

    def patch(self, request, pk):
        fabric = self.get_object(pk)
        if not fabric:
            return error("Fabric not found", status_code=status.HTTP_404_NOT_FOUND)
        if not is_tailor(request.user) or fabric.tailor != request.user.tailor:
            return error("Permission denied", status_code=status.HTTP_403_FORBIDDEN)

        serializer = FabricSerializer(fabric, data=request.data, partial=True, context={'request': request})
        if not serializer.is_valid():
            return error("Update failed", errors=serializer.errors)
        serializer.save()
        return success(data=serializer.data, msg="Fabric updated")

    def delete(self, request, pk):
        fabric = self.get_object(pk)
        if not fabric:
            return error("Fabric not found", status_code=status.HTTP_404_NOT_FOUND)
        if not is_tailor(request.user) or fabric.tailor != request.user.tailor:
            return error("Permission denied", status_code=status.HTTP_403_FORBIDDEN)
        fabric.delete()
        return success(msg="Fabric deleted")

# ─────────────────────────────────────────
#  EMBROIDERY
# ─────────────────────────────────────────
class EmbroideryListCreateView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes     = [MultiPartParser, FormParser, JSONParser]

    def get(self, request):
        tailor_id = request.query_params.get('tailor_id')

        if tailor_id:
            qs = Embroidery.objects.filter(
                tailor_id=tailor_id, is_available=True
            ).select_related('tailor')
        elif is_tailor(request.user):
            qs = Embroidery.objects.filter(
                tailor=request.user.tailor
            ).select_related('tailor')
        else:
            qs = Embroidery.objects.filter(is_available=True).select_related('tailor')

        data = EmbroiderySerializer(qs, many=True, context={'request': request}).data
        return success(data=data)

    def post(self, request):
        if not is_tailor(request.user):
            return error("Only tailors can add embroidery", status_code=status.HTTP_403_FORBIDDEN)

        serializer = EmbroiderySerializer(data=request.data, context={'request': request})
        if not serializer.is_valid():
            return error("Failed to add embroidery", errors=serializer.errors)

        serializer.save(tailor=request.user.tailor)
        return success(data=serializer.data, msg="Embroidery added", status_code=status.HTTP_201_CREATED)

class EmbroideryDetailView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes     = [MultiPartParser, FormParser, JSONParser]

    def get_object(self, pk):
        return Embroidery.objects.filter(pk=pk).select_related('tailor').first()

    def get(self, request, pk):
        embroidery = self.get_object(pk)
        if not embroidery:
            return error("Embroidery not found", status_code=status.HTTP_404_NOT_FOUND)
        return success(data=EmbroiderySerializer(embroidery, context={'request': request}).data)

    def patch(self, request, pk):
        embroidery = self.get_object(pk)
        if not embroidery:
            return error("Embroidery not found", status_code=status.HTTP_404_NOT_FOUND)
        if not is_tailor(request.user) or embroidery.tailor != request.user.tailor:
            return error("Permission denied", status_code=status.HTTP_403_FORBIDDEN)

        serializer = EmbroiderySerializer(embroidery, data=request.data, partial=True, context={'request': request})
        if not serializer.is_valid():
            return error("Update failed", errors=serializer.errors)
        serializer.save()
        return success(data=serializer.data, msg="Embroidery updated")

    def delete(self, request, pk):
        embroidery = self.get_object(pk)
        if not embroidery:
            return error("Embroidery not found", status_code=status.HTTP_404_NOT_FOUND)
        if not is_tailor(request.user) or embroidery.tailor != request.user.tailor:
            return error("Permission denied", status_code=status.HTTP_403_FORBIDDEN)
        embroidery.delete()
        return success(msg="Embroidery deleted")

# ─────────────────────────────────────────
#  PRE-DRESS
# ─────────────────────────────────────────
class PreDressListCreateView(APIView):
    permission_classes = [AllowAny]
    parser_classes     = [MultiPartParser, FormParser, JSONParser]

    def get(self, request):
        qs = PreDress.objects.all().select_related(
            'tailor', 'fabric', 'embroidery'
        ).prefetch_related('images').order_by('-created_at')

        # Filters
        tailor_id = request.query_params.get('tailor_id')
        category  = request.query_params.get('category')
        search    = request.query_params.get('search')
        featured  = request.query_params.get('featured')
        min_price = request.query_params.get('min_price')
        max_price = request.query_params.get('max_price')

        if tailor_id:
            qs = qs.filter(tailor_id=tailor_id)
        if category:
            qs = qs.filter(category__icontains=category)
        if search:
            qs = qs.filter(
                Q(title__icontains=search) |
                Q(description__icontains=search) |
                Q(tags__icontains=search)
            )
        if featured == 'true':
            qs = qs.filter(is_featured=True)
        if min_price:
            qs = qs.filter(price__gte=min_price)
        if max_price:
            qs = qs.filter(price__lte=max_price)

        data = PreDressCardSerializer(qs, many=True, context={'request': request}).data
        return success(data=data)

    def post(self, request):
        if not request.user.is_authenticated or not is_tailor(request.user):
            return error("Only tailors can add dresses", status_code=status.HTTP_403_FORBIDDEN)

        serializer = PreDressDetailSerializer(data=request.data, context={'request': request})
        if not serializer.is_valid():
            return error("Failed to add dress", errors=serializer.errors)

        pre_dress = serializer.save(tailor=request.user.tailor)

        # Multiple image upload
        images = request.FILES.getlist('images')
        for index, img in enumerate(images):
            PreDressImage.objects.create(
                pre_dress  = pre_dress,
                image      = img,
                is_primary = index == 0,
                order      = index,
            )

        return success(
            data       = PreDressDetailSerializer(pre_dress, context={'request': request}).data,
            msg        = "Dress added successfully",
            status_code= status.HTTP_201_CREATED,
        )

class PreDressDetailView(APIView):
    permission_classes = [AllowAny]
    parser_classes     = [MultiPartParser, FormParser, JSONParser]

    def get_object(self, pk):
        return PreDress.objects.filter(pk=pk).select_related(
            'tailor', 'fabric', 'embroidery'
        ).prefetch_related('images').first()

    def get(self, request, pk):
        pre_dress = self.get_object(pk)
        if not pre_dress:
            return error("Dress not found", status_code=status.HTTP_404_NOT_FOUND)
        data = PreDressDetailSerializer(pre_dress, context={'request': request}).data
        return success(data=data)

    def patch(self, request, pk):
        pre_dress = self.get_object(pk)
        if not pre_dress:
            return error("Dress not found", status_code=status.HTTP_404_NOT_FOUND)
        if not is_tailor(request.user) or pre_dress.tailor != request.user.tailor:
            return error("Permission denied", status_code=status.HTTP_403_FORBIDDEN)

        serializer = PreDressDetailSerializer(
            pre_dress, data=request.data, partial=True, context={'request': request}
        )
        if not serializer.is_valid():
            return error("Update failed", errors=serializer.errors)
        serializer.save()
        return success(data=serializer.data, msg="Dress updated")

    def delete(self, request, pk):
        pre_dress = self.get_object(pk)
        if not pre_dress:
            return error("Dress not found", status_code=status.HTTP_404_NOT_FOUND)
        if not is_tailor(request.user) or pre_dress.tailor != request.user.tailor:
            return error("Permission denied", status_code=status.HTTP_403_FORBIDDEN)
        pre_dress.delete()
        return success(msg="Dress deleted")

class PreDressImageUploadView(APIView):
    """Extra images add / delete করার জন্য।"""
    permission_classes = [IsAuthenticated]
    parser_classes     = [MultiPartParser, FormParser, JSONParser] 

    def post(self, request, pk):
        pre_dress = PreDress.objects.filter(pk=pk).first()
        if not pre_dress:
            return error("Dress not found", status_code=status.HTTP_404_NOT_FOUND)
        if pre_dress.tailor != request.user.tailor:
            return error("Permission denied", status_code=status.HTTP_403_FORBIDDEN)

        images  = request.FILES.getlist('images')
        created = []
        current_count = pre_dress.images.count()

        for index, img in enumerate(images):
            obj = PreDressImage.objects.create(
                pre_dress  = pre_dress,
                image      = img,
                is_primary = current_count == 0 and index == 0,
                order      = current_count + index,
            )
            created.append(PreDressImageSerializer(obj, context={'request': request}).data)

        return success(data=created, msg="Images uploaded", status_code=status.HTTP_201_CREATED)

    def delete(self, request, pk):
        image_id = request.data.get('image_id')
        image    = PreDressImage.objects.filter(pk=image_id, pre_dress_id=pk).first()
        if not image:
            return error("Image not found", status_code=status.HTTP_404_NOT_FOUND)
        if image.pre_dress.tailor != request.user.tailor:
            return error("Permission denied", status_code=status.HTTP_403_FORBIDDEN)
        image.delete()
        return success(msg="Image deleted")

# ─────────────────────────────────────────
#  PRE-DRESS ORDER
# ─────────────────────────────────────────
class PreDressOrderCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        # Allow both customer and tailor to place orders
        if not is_customer(request.user) and not is_tailor(request.user):
            return error("Only customers or tailors can place orders", status_code=status.HTTP_403_FORBIDDEN)

        serializer = PreDressOrderCreateSerializer(
            data    = request.data,
            context = {'request': request},
        )
        if not serializer.is_valid():
            return error("Order failed", errors=serializer.errors)

        order = serializer.save()
        
        # If tailor is placing order, set customer to None or create a customer profile
        if is_tailor(request.user) and not is_customer(request.user):
            order.customer = None
            order.save(update_fields=['customer'])
        
        data  = PreDressOrderSerializer(order).data
        return success(data=data, msg="Order placed successfully", status_code=status.HTTP_201_CREATED)

class PreDressOrderListView(APIView):
    """Customer-এর নিজের Pre-Dress Order list — 'My Order' tab-এর জন্য।"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # শুধুমাত্র customer এর নিজের orders দেখাবে
        if not is_customer(request.user):
            return error("Only customers can access this", status_code=status.HTTP_403_FORBIDDEN)

        qs = PreDressOrder.objects.filter(
            customer=request.user.customer
        ).select_related('pre_dress', 'tailor', 'customer').order_by('-ordered_at')

        status_filter = request.query_params.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter)

        data = PreDressOrderSerializer(qs, many=True).data
        return success(data=data)


class PreDressOrderDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, pk, user):
        qs = PreDressOrder.objects.select_related('pre_dress', 'tailor', 'customer')
        if is_tailor(user):
            order = qs.filter(pk=pk, tailor=user.tailor).first()
            if order:
                return order
        if is_customer(user):
            return qs.filter(pk=pk, customer=user.customer).first()
        return None

    def get(self, request, pk):
        order = self.get_object(pk, request.user)
        if not order:
            return error("Order not found", status_code=status.HTTP_404_NOT_FOUND)
        return success(data=PreDressOrderSerializer(order).data)

    def patch(self, request, pk):
        # শুধু tailor status update করতে পারবে
        if not is_tailor(request.user):
            return error("Permission denied", status_code=status.HTTP_403_FORBIDDEN)

        order = PreDressOrder.objects.filter(pk=pk, tailor=request.user.tailor).first()
        if not order:
            return error("Order not found", status_code=status.HTTP_404_NOT_FOUND)

        serializer = PreDressOrderStatusUpdateSerializer(order, data=request.data, partial=True)
        if not serializer.is_valid():
            return error("Update failed", errors=serializer.errors)
        serializer.save()
        return success(data=PreDressOrderSerializer(order).data, msg="Order updated")

# ─────────────────────────────────────────
#  TAILOR ORDER
# ─────────────────────────────────────────
class TailorOrderCreateView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes     = [MultiPartParser, FormParser, JSONParser]

    def post(self, request):
        if not is_customer(request.user) and not is_tailor(request.user):
            return error("Only customers or tailors can place orders", status_code=status.HTTP_403_FORBIDDEN)

        serializer = TailorOrderCreateSerializer(
            data    = request.data,
            context = {'request': request},
        )
        if not serializer.is_valid():
            return error("Order failed", errors=serializer.errors)

        order = serializer.save()
        
        # If tailor is placing order, set customer to None
        if is_tailor(request.user) and not is_customer(request.user):
            order.customer = None
            order.save(update_fields=['customer'])
        
        data  = TailorOrderSerializer(order).data
        return success(data=data, msg="Order placed successfully", status_code=status.HTTP_201_CREATED)

class TailorOrderListView(APIView):
    """Customer-এর নিজের Tailor Order list — 'My Order' tab-এর জন্য।"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # শুধুমাত্র customer এর নিজের orders দেখাবে
        if not is_customer(request.user):
            return error("Only customers can access this", status_code=status.HTTP_403_FORBIDDEN)

        qs = TailorOrder.objects.filter(
            customer=request.user.customer
        ).select_related('tailor', 'customer', 'fabric', 'embroidery').order_by('-ordered_at')

        status_filter = request.query_params.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter)

        data = TailorOrderSerializer(qs, many=True).data
        return success(data=data)


class TailorOrderDetailView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes     = [MultiPartParser, FormParser, JSONParser]

    def get_object(self, pk, user):
        qs = TailorOrder.objects.select_related('tailor', 'customer', 'fabric', 'embroidery')
        if is_tailor(user):
            order = qs.filter(pk=pk, tailor=user.tailor).first()
            if order:
                return order
        if is_customer(user):
            return qs.filter(pk=pk, customer=user.customer).first()
        return None

    def get(self, request, pk):
        order = self.get_object(pk, request.user)
        if not order:
            return error("Order not found", status_code=status.HTTP_404_NOT_FOUND)
        return success(data=TailorOrderSerializer(order).data)

    def patch(self, request, pk):
        if not is_tailor(request.user):
            return error("Permission denied", status_code=status.HTTP_403_FORBIDDEN)

        order = TailorOrder.objects.filter(pk=pk, tailor=request.user.tailor).first()
        if not order:
            return error("Order not found", status_code=status.HTTP_404_NOT_FOUND)

        serializer = TailorOrderPricingSerializer(order, data=request.data, partial=True)
        if not serializer.is_valid():
            return error("Update failed", errors=serializer.errors)
        serializer.save()
        return success(data=TailorOrderSerializer(order).data, msg="Order updated")

    def delete(self, request, pk):
        # শুধু customer cancel করতে পারবে pending থাকলে
        if not is_customer(request.user):
            return error("Permission denied", status_code=status.HTTP_403_FORBIDDEN)

        order = TailorOrder.objects.filter(
            pk=pk, customer=request.user.customer
        ).first()
        if not order:
            return error("Order not found", status_code=status.HTTP_404_NOT_FOUND)
        if order.status != 'pending':
            return error("Only pending orders can be cancelled")

        order.status = 'cancelled'
        order.save(update_fields=['status'])
        return success(msg="Order cancelled")

# ─────────────────────────────────────────
#  REVIEW
# ─────────────────────────────────────────
class ReviewListCreateView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        tailor_id    = request.query_params.get('tailor_id')
        pre_dress_id = request.query_params.get('pre_dress_id')

        qs = Review.objects.filter(
            is_visible=True
        ).select_related('customer__user').order_by('-created_at')

        if tailor_id:
            qs = qs.filter(tailor_id=tailor_id)
        if pre_dress_id:
            qs = qs.filter(pre_dress_id=pre_dress_id)

        data = ReviewSerializer(qs, many=True, context={'request': request}).data
        return success(data=data)

    def post(self, request):
        if not request.user.is_authenticated or not is_customer(request.user):
            return error("Only customers can write reviews", status_code=status.HTTP_403_FORBIDDEN)

        serializer = ReviewSerializer(data=request.data, context={'request': request})
        if not serializer.is_valid():
            return error("Review failed", errors=serializer.errors)

        review = serializer.save()
        self._update_rating_cache(review)

        return success(
            data       = ReviewSerializer(review, context={'request': request}).data,
            msg        = "Review submitted",
            status_code= status.HTTP_201_CREATED,
        )

    def _update_rating_cache(self, review):
        """Rating cache update — signal এর বদলে এখানে করি।"""
        from django.db.models import Avg, Count

        if review.tailor:
            result = Review.objects.filter(
                tailor=review.tailor, is_visible=True
            ).aggregate(avg=Avg('rating'), count=Count('id'))

            review.tailor.average_rating = result['avg'] or 0
            review.tailor.total_reviews  = result['count']
            review.tailor.save(update_fields=['average_rating', 'total_reviews'])

        if review.pre_dress:
            result = Review.objects.filter(
                pre_dress=review.pre_dress, is_visible=True
            ).aggregate(avg=Avg('rating'), count=Count('id'))

            review.pre_dress.average_rating = result['avg'] or 0
            review.pre_dress.total_reviews  = result['count']
            review.pre_dress.save(update_fields=['average_rating', 'total_reviews'])

class ReviewDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, pk):
        return Review.objects.filter(pk=pk).select_related('customer__user').first()

    def get(self, request, pk):
        review = self.get_object(pk)
        if not review:
            return error("Review not found", status_code=status.HTTP_404_NOT_FOUND)
        return success(data=ReviewSerializer(review, context={'request': request}).data)

    def patch(self, request, pk):
        review = self.get_object(pk)
        if not review:
            return error("Review not found", status_code=status.HTTP_404_NOT_FOUND)
        if review.customer != request.user.customer:
            return error("Permission denied", status_code=status.HTTP_403_FORBIDDEN)

        serializer = ReviewSerializer(review, data=request.data, partial=True, context={'request': request})
        if not serializer.is_valid():
            return error("Update failed", errors=serializer.errors)
        serializer.save()
        return success(data=serializer.data, msg="Review updated")

    def delete(self, request, pk):
        review = self.get_object(pk)
        if not review:
            return error("Review not found", status_code=status.HTTP_404_NOT_FOUND)
        if review.customer != request.user.customer:
            return error("Permission denied", status_code=status.HTTP_403_FORBIDDEN)
        review.delete()
        return success(msg="Review deleted")

# ─────────────────────────────────────────
#  NOTIFICATION
# ─────────────────────────────────────────
class NotificationListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = Notification.objects.filter(
            recipient=request.user
        ).order_by('-created_at')

        # Filter unread only
        unread_only = request.query_params.get('unread')
        if unread_only == 'true':
            qs = qs.filter(is_read=False)

        # Filter by type
        ntype = request.query_params.get('type')
        if ntype:
            qs = qs.filter(notification_type=ntype)

        data = NotificationSerializer(qs, many=True).data

        # Unread count
        unread_count = Notification.objects.filter(
            recipient=request.user, is_read=False
        ).count()

        return success(data={'notifications': data, 'unread_count': unread_count})

class NotificationMarkReadView(APIView):
    """Single notification mark as read।"""
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        notif = Notification.objects.filter(pk=pk, recipient=request.user).first()
        if not notif:
            return error("Notification not found", status_code=status.HTTP_404_NOT_FOUND)
        notif.mark_as_read()
        return success(msg="Marked as read")

class NotificationMarkAllReadView(APIView):
    """সব notification একসাথে read করা।"""
    permission_classes = [IsAuthenticated]

    def patch(self, request):
        Notification.objects.filter(
            recipient=request.user, is_read=False
        ).update(is_read=True, read_at=timezone.now())
        return success(msg="All notifications marked as read")

class NotificationDeleteView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk):
        notif = Notification.objects.filter(pk=pk, recipient=request.user).first()
        if not notif:
            return error("Notification not found", status_code=status.HTTP_404_NOT_FOUND)
        notif.delete()
        return success(msg="Notification deleted")

    def delete_all(self, request):
        Notification.objects.filter(recipient=request.user).delete()
        return success(msg="All notifications cleared")

class NotificationUnreadCountView(APIView):
    """Polling বা badge update এর জন্য।"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        count = Notification.objects.filter(
            recipient=request.user, is_read=False
        ).count()
        return success(data={'unread_count': count})

# ─────────────────────────────────────────
#  CONVERSATION
# ─────────────────────────────────────────
class ConversationListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if is_customer(request.user):
            qs = Conversation.objects.filter(
                customer=request.user.customer
            ).select_related('customer__user', 'tailor').order_by('-last_message_at')

        elif is_tailor(request.user):
            qs = Conversation.objects.filter(
                tailor=request.user.tailor
            ).select_related('customer__user', 'tailor').order_by('-last_message_at')
        else:
            return error("Permission denied", status_code=status.HTTP_403_FORBIDDEN)

        data = ConversationListSerializer(qs, many=True).data
        return success(data=data)

    def post(self, request):
        """Customer tailor এর সাথে conversation শুরু করবে।"""
        if not is_customer(request.user):
            return error("Only customers can start conversations", status_code=status.HTTP_403_FORBIDDEN)

        tailor_id = request.data.get('tailor_id')
        tailor    = Tailor.objects.filter(pk=tailor_id).first()
        if not tailor:
            return error("Tailor not found", status_code=status.HTTP_404_NOT_FOUND)

        # Already exists হলে সেটাই return করো
        conversation, created = Conversation.objects.get_or_create(
            customer = request.user.customer,
            tailor   = tailor,
        )
        data = ConversationSerializer(conversation).data
        return success(
            data       = data,
            msg        = "Conversation started" if created else "Existing conversation",
            status_code= status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

class ConversationDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, pk, user):
        qs = Conversation.objects.prefetch_related(...).select_related(...)
        if is_tailor(user):
            conv = qs.filter(pk=pk, tailor=user.tailor).first()
            if conv:
                return conv
        if is_customer(user):
            return qs.filter(pk=pk, customer=user.customer).first()
        return None

    def get(self, request, pk):
        conversation = self.get_object(pk, request.user)
        if not conversation:
            return error("Conversation not found", status_code=status.HTTP_404_NOT_FOUND)

        # Unread reset
        if is_customer(request.user):
            Conversation.objects.filter(pk=pk).update(customer_unread=0)
            Message.objects.filter(
                conversation=conversation, is_read=False
            ).exclude(sender=request.user).update(is_read=True, read_at=timezone.now())

        elif is_tailor(request.user):
            Conversation.objects.filter(pk=pk).update(tailor_unread=0)
            Message.objects.filter(
                conversation=conversation, is_read=False
            ).exclude(sender=request.user).update(is_read=True, read_at=timezone.now())

        data = ConversationSerializer(conversation).data
        return success(data=data)

# ─────────────────────────────────────────
#  MESSAGE
# ─────────────────────────────────────────
class MessageSendView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes     = [MultiPartParser, FormParser, JSONParser]

    def post(self, request, conversation_id):
        # Conversation টা এই user এর কিনা
        if is_customer(request.user):
            conversation = Conversation.objects.filter(
                pk=conversation_id, customer=request.user.customer
            ).first()
        elif is_tailor(request.user):
            conversation = Conversation.objects.filter(
                pk=conversation_id, tailor=request.user.tailor
            ).first()
        else:
            return error("Permission denied", status_code=status.HTTP_403_FORBIDDEN)

        if not conversation:
            return error("Conversation not found", status_code=status.HTTP_404_NOT_FOUND)

        content = request.data.get('content', '').strip()
        images  = request.FILES.getlist('images')

        if not content and not images:
            return error("Message content or image required")

        message = Message.objects.create(
            conversation = conversation,
            sender       = request.user,
            content      = content,
        )

        for img in images:
            caption = request.data.get('caption', '')
            MessageImage.objects.create(message=message, image=img, caption=caption)

        # Conversation last message update
        preview = content[:100] if content else "📷 Image"
        if is_customer(request.user):
            Conversation.objects.filter(pk=conversation_id).update(
                last_message_at      = timezone.now(),
                last_message_preview = preview,
                tailor_unread        = conversation.tailor_unread + 1,
            )
        else:
            Conversation.objects.filter(pk=conversation_id).update(
                last_message_at      = timezone.now(),
                last_message_preview = preview,
                customer_unread      = conversation.customer_unread + 1,
            )

        data = MessageSerializer(message, context={'request': request}).data
        return success(data=data, msg="Message sent", status_code=status.HTTP_201_CREATED)

class MessageDeleteView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk):
        message = Message.objects.filter(pk=pk, sender=request.user).first()
        if not message:
            return error("Message not found", status_code=status.HTTP_404_NOT_FOUND)
        message.delete()
        return success(msg="Message deleted")

# ─────────────────────────────────────────
#  TAILOR MY ORDERS  (orders placed BY this tailor as customer)
# ─────────────────────────────────────────

class MyTailorOrderListView(APIView):
    """Tailor-এর নিজের Shop Order list — 'Shop Order' tab-এর জন্য।"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not is_tailor(request.user):
            return error("Only tailors can access this", status_code=status.HTTP_403_FORBIDDEN)

        qs = TailorOrder.objects.filter(
            tailor__user=request.user
        ).select_related('tailor', 'customer', 'fabric', 'embroidery').order_by('-ordered_at')

        status_filter = request.query_params.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter)

        data = TailorOrderSerializer(qs, many=True).data
        return success(data=data)


class MyPreDressOrderListView(APIView):
    """Tailor-এর নিজের Pre-Dress Shop Order list — 'Shop Order' tab-এর জন্য।"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not is_tailor(request.user):
            return error("Only tailors can access this", status_code=status.HTTP_403_FORBIDDEN)

        qs = PreDressOrder.objects.filter(
            tailor__user=request.user
        ).select_related('pre_dress', 'tailor', 'customer').order_by('-ordered_at')

        status_filter = request.query_params.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter)

        data = PreDressOrderSerializer(qs, many=True).data
        return success(data=data)