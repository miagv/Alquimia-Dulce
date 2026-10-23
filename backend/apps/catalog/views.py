from django.db.models import Prefetch, Q
from rest_framework import generics, permissions

from .models import Category, Product, ProductImage, ProductVariant
from .serializers import CategorySerializer, ProductSerializer


class CategoryListView(generics.ListAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = CategorySerializer
    pagination_class = None
    queryset = Category.objects.filter(is_active=True)


class ProductQuerysetMixin:
    def get_queryset(self):
        queryset = Product.objects.filter(
            is_available=True,
            category__is_active=True,
            variants__is_active=True,
        ).select_related('category').prefetch_related(
            Prefetch(
                'variants',
                queryset=ProductVariant.objects.filter(is_active=True).order_by('price'),
                to_attr='active_variants',
            ),
            Prefetch('images', queryset=ProductImage.objects.order_by('display_order'), to_attr='product_images'),
        ).distinct()

        category = self.request.query_params.get('category')
        search = self.request.query_params.get('search')
        featured = self.request.query_params.get('featured')
        in_stock = self.request.query_params.get('in_stock')

        if category:
            queryset = queryset.filter(category__slug=category)
        if search:
            queryset = queryset.filter(Q(name__icontains=search) | Q(description__icontains=search))
        if featured == 'true':
            queryset = queryset.filter(is_featured=True)
        if in_stock == 'true':
            queryset = queryset.filter(variants__stock__gt=0)

        return queryset


class ProductListView(ProductQuerysetMixin, generics.ListAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = ProductSerializer


class ProductDetailView(ProductQuerysetMixin, generics.RetrieveAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = ProductSerializer
    lookup_field = 'slug'
