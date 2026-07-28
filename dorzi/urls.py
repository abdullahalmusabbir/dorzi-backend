"""
URL configuration for dorzi project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.shortcuts import redirect
from django.urls import path,re_path
from django.conf import settings
from django.conf.urls.static import static
from . import views
from django.contrib.auth import views as auth_views
from django.views.static import serve
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

urlpatterns = [
    path('iloveumusabbir/', admin.site.urls, name='superadmin'),
    
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    
    # ── Auth ──────────────────────────────────
    path('auth/register/customer/',views.CustomerRegisterView.as_view(), name='customer-register'),
    path('auth/register/tailor/',views.TailorRegisterView.as_view(), name='tailor-register'),
    path('auth/login/',views.LoginView.as_view(), name='login'),
    path('auth/logout/',views.LogoutView.as_view(), name='logout'),
    path('auth/token/refresh/',TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/forgot-password/',views.ForgotPasswordView.as_view(), name='forgot-password'),
    path('auth/reset-password/<uid>/<token>/',views.ResetPasswordView.as_view(), name='reset-password'),
    path('auth/change-password/',views.ChangePasswordView.as_view(), name='change-password'),
    path('auth/google/',views.GoogleLoginView.as_view(), name='google-login'),

    # ── Customer ──────────────────────────────
    path('customer/profile/',views.CustomerProfileView.as_view(), name='customer-profile'),
    path('customer/measurements/',views.CustomerMeasurementView.as_view(), name='customerMeasurements'),
    path('tailors/',views.TailorListView.as_view(), name='tailor-list'),
    path('tailors/<int:pk>/',views.TailorDetailView.as_view(), name='tailor-detail'),
    path('tailor/profile/',views.MyTailorProfileView.as_view(), name='my-tailor-profile'),
    path('tailor/measurements/', views.TailorMeasurementView.as_view(), name='tailor-measurements'),

    # ── Fabric ────────────────────────────────
    path('fabrics/',views.FabricListCreateView.as_view(), name='fabric-list'),
    path('fabrics/<int:pk>/',views.FabricDetailView.as_view(), name='fabric-detail'),

    # ── Embroidery ────────────────────────────
    path('embroideries/',views.EmbroideryListCreateView.as_view(), name='embroidery-list'),
    path('embroideries/<int:pk>/',views.EmbroideryDetailView.as_view(), name='embroidery-detail'),

    # ── Pre-Dress ─────────────────────────────
    path('pre-dresses/',views.PreDressListCreateView.as_view(), name='pre-dress-list'),
    path('pre-dresses/<uuid:pk>/',views.PreDressDetailView.as_view(), name='pre-dress-detail'),
    path('pre-dresses/<uuid:pk>/images/', views.PreDressImageUploadView.as_view(), name='pre-dress-image-upload'),

    # ── Pre-Dress Order ───────────────────────
    path('orders/pre-dress/',views.PreDressOrderListView.as_view(), name='pre-dress-order-list'),
    path('orders/pre-dress/create/',views.PreDressOrderCreateView.as_view(), name='pre-dress-order-create'),
    path('orders/pre-dress/<uuid:pk>/',views.PreDressOrderDetailView.as_view(), name='pre-dress-order-detail'),

    # ── Tailor Order ──────────────────────────
    path('orders/tailor/',views.TailorOrderListView.as_view(), name='tailor-order-list'),
    path('orders/tailor/create/',views.TailorOrderCreateView.as_view(), name='tailor-order-create'),
    path('orders/tailor/<uuid:pk>/',views.TailorOrderDetailView.as_view(), name='tailor-order-detail'),
    
    # ── Tailor My Orders ─────────────────────────
    path('orders/tailor/my-orders/', views.MyTailorOrderListView.as_view(), name='my-tailor-order-list'),
    path('orders/pre-dress/my-orders/', views.MyPreDressOrderListView.as_view(), name='my-pre-dress-order-list'),

    # ── Review ────────────────────────────────
    path('reviews/',views.ReviewListCreateView.as_view(), name='review-list'),
    path('reviews/<int:pk>/',views.ReviewDetailView.as_view(), name='review-detail'),

    # ── Notification ──────────────────────────
    path('notifications/',views.NotificationListView.as_view(), name='notification-list'),
    path('notifications/unread-count/',views.NotificationUnreadCountView.as_view(), name='notification-unread-count'),
    path('notifications/mark-all-read/',views.NotificationMarkAllReadView.as_view(), name='notification-mark-all-read'),
    path('notifications/<int:pk>/mark-read/',views.NotificationMarkReadView.as_view(), name='notification-mark-read'),
    path('notifications/<int:pk>/delete/',views.NotificationDeleteView.as_view(), name='notification-delete'),

    # ── Conversation ──────────────────────────
    path('conversations/',views.ConversationListCreateView.as_view(), name='conversation-list'),
    path('conversations/<uuid:pk>/',views.ConversationDetailView.as_view(), name='conversation-detail'),

    # ── Message ───────────────────────────────
    path('conversations/<uuid:conversation_id>/messages/', views.MessageSendView.as_view(), name='message-send'),
    path('messages/<uuid:pk>/delete/',views.MessageDeleteView.as_view(), name='message-delete'),
]

urlpatterns += [
    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
]