from .serializers import (AvatarSerializer, FollowSerializer,
                          IngredientSerializer, RecipeMiniSerializer,
                          RecipeReadSerializer, RecipeWriteSerializer,
                          TagSerializer, UserSerializer)
from recipes.models import Favorite, Ingredient, Recipe, ShoppingCart, Tag, RecipeIngredient
from users.models import Follow, User
from rest_framework import status, viewsets
from rest_framework.permissions import (AllowAny, IsAuthenticated,
                                        IsAuthenticatedOrReadOnly)
from django_filters.rest_framework import DjangoFilterBackend
from .filters import IngredientFilter, RecipeFilter
from .pagination import StandardResultsSetPagination
from .permissions import IsCreatorOrReadOnly
from djoser.views import UserViewSet as DjoserUserViewSet
from rest_framework.response import Response
from rest_framework.decorators import action
from django.shortcuts import get_object_or_404
from django.db.models import Count

class TagViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = [AllowAny]
    pagination_class = None


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    permission_classes = [AllowAny]
    pagination_class = None
    filter_backends = [DjangoFilterBackend]
    filterset_class = IngredientFilter


class RecipeViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticatedOrReadOnly, IsCreatorOrReadOnly]
    filter_backends = [DjangoFilterBackend]
    filterset_class = RecipeFilter
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        return Recipe.objects.with_user_annotations(self.request.user).order_by('-pub_date')

    def get_serializer_class(self):
        if self.action in ('list', 'retrieve'):
            return RecipeReadSerializer
        return RecipeWriteSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        read_serializer = RecipeReadSerializer(serializer.instance, context=self.get_serializer_context())
        return Response(read_serializer.data, status=status.HTTP_201_CREATED)

    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(
            instance, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)  # 🔒 критично — чтобы валидаторы работали
        serializer.save()
        return Response(
            serializer.data, status=status.HTTP_200_OK
        )

    def _toggle_relation(self, request, pk, model):
        recipe = get_object_or_404(Recipe, pk=pk)
        relation, created = model.objects.get_or_create(user=request.user, recipe=recipe)

        if not created:
            relation.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

        serializer = RecipeMiniSerializer(recipe)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post', 'delete'], permission_classes=[IsAuthenticated])
    def favorite(self, request, pk=None):
        user = request.user
        recipe = get_object_or_404(Recipe, pk=pk)

        if request.method == 'DELETE':
            favorite = Favorite.objects.filter(user=user, recipe=recipe)
            if favorite.exists():
                favorite.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            return Response({'errors': 'Рецепт не в избранном'}, status=status.HTTP_400_BAD_REQUEST)

        if Favorite.objects.filter(user=user, recipe=recipe).exists():
            return Response(
                {"errors": "Рецепт уже в избранном."},
                status=status.HTTP_400_BAD_REQUEST
            )

        Favorite.objects.create(user=user, recipe=recipe)
        serializer = RecipeMiniSerializer(recipe, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)

class UserViewSet(DjoserUserViewSet):
    queryset = User.objects.all()
    permission_classes = [AllowAny]
    pagination_class = StandardResultsSetPagination

    @action(
        detail=False,
        methods=['get'],
        permission_classes=[IsAuthenticated],
        serializer_class=UserSerializer,
        pagination_class=None
    )
    def me(self, request, *args, **kwargs):
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)

    @action(
        detail=False,
        methods=['get'],
        permission_classes=[IsAuthenticated],
        url_path='subscriptions',
        serializer_class=FollowSerializer
    )
    def subscriptions(self, request):
        queryset = User.objects.filter(
            followers__user=request.user
        ).annotate(recipes_count=Count('recipes')).order_by('username')

        page = self.paginate_queryset(queryset)
        serializer = self.get_serializer(page, many=True, context={'request': request})
        return self.get_paginated_response(serializer.data)

    @action(detail=True, methods=['post', 'delete'], permission_classes=[IsAuthenticated])
    def subscribe(self, request, id=None):
        author = get_object_or_404(User, id=id)

        if request.user == author:
            return Response(
                {'errors': 'You cannot subscribe to yourself.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        follow_exists = Follow.objects.filter(user=request.user, author=author).exists()

        if request.method == 'POST':
            if follow_exists:
                return Response(
                    {'errors': 'You are already subscribed to this author.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            Follow.objects.create(user=request.user, author=author)
            serializer = FollowSerializer(author, context={'request': request})
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        if not follow_exists:
            return Response(
                {'errors': 'You are not subscribed to this author.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        Follow.objects.filter(user=request.user, author=author).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
