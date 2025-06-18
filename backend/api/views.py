from .serializers import (
    AvatarSerializer,
    FollowSerializer,
    IngredientSerializer,
    RecipeMiniSerializer,
    RecipeReadSerializer,
    RecipeWriteSerializer,
    UserSerializer,
)
from recipes.models import (
    Favorite,
    Ingredient,
    Recipe,
    ShoppingCart,
    RecipeIngredient,
)
from users.models import Follow, User
from rest_framework import status, viewsets
from rest_framework.permissions import (
    AllowAny,
    IsAuthenticated,
    IsAuthenticatedOrReadOnly,
)
from django_filters.rest_framework import DjangoFilterBackend
from .filters import IngredientFilter, RecipeFilter
from .pagination import StandardResultsSetPagination
from .permissions import IsCreatorOrReadOnly
from djoser.views import UserViewSet as DjoserUserViewSet
from rest_framework.response import Response
from rest_framework.decorators import action
from django.shortcuts import get_object_or_404
from django.db.models import Count, Sum
from django.http import HttpResponse


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
        return Recipe.objects.with_user_annotations(self.request.user).order_by(
            "-pub_date"
        )

    def get_serializer_class(self):
        if self.action in ("list", "retrieve"):
            return RecipeReadSerializer
        return RecipeWriteSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        read_serializer = RecipeReadSerializer(
            serializer.instance, context=self.get_serializer_context()
        )
        return Response(read_serializer.data, status=status.HTTP_201_CREATED)

    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(
        detail=True, methods=["post", "delete"], permission_classes=[IsAuthenticated]
    )
    def favorite(self, request, pk=None):
        user = request.user
        recipe = get_object_or_404(Recipe, pk=pk)

        if request.method == "DELETE":
            favorite_relation = user.favorite_relations.filter(recipe=recipe)
            if favorite_relation.exists():
                favorite_relation.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            return Response(
                {"errors": "Рецепт не в избранном"}, status=status.HTTP_400_BAD_REQUEST
            )
        if user.favorite_relations.filter(recipe=recipe).exists():
            return Response(
                {"errors": "Рецепт уже в избранном."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        Favorite.objects.create(user=user, recipe=recipe)
        serializer = RecipeMiniSerializer(recipe, context={"request": request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(
        detail=True, methods=["post", "delete"], permission_classes=[IsAuthenticated]
    )
    def shopping_cart(self, request, pk=None):
        user = request.user
        recipe = get_object_or_404(Recipe, pk=pk)

        if request.method == "DELETE":
            cart_item = user.shopping_cart.filter(recipe=recipe)
            if cart_item.exists():
                cart_item.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            return Response(
                {"errors": "Рецепт не в корзине"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if user.shopping_cart.filter(recipe=recipe).exists():
            return Response(
                {"errors": "Рецепт уже в списке покупок."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        ShoppingCart.objects.create(user=user, recipe=recipe)
        serializer = RecipeMiniSerializer(recipe, context={"request": request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(
        detail=True, methods=["get"], permission_classes=[AllowAny], url_path="get-link"
    )
    def get_link(self, request, pk=None):
        recipe = self.get_object()
        recipe_path = f"/api/recipes/{recipe.pk}/"
        try:
            link = request.build_absolute_uri(recipe_path)
            response_data = {"short-link": link}
            return Response(response_data, status=status.HTTP_200_OK)
        except Exception:
            return Response(
                {"error": "Could not generate link."},
                status=status.HTTP_400_BAD_REQUEST,
            )

    @action(detail=False, methods=["get"], url_path="download_shopping_cart")
    def download_shopping_cart(self, request):
        user = request.user

        recipes = Recipe.objects.filter(shopping_cart__user=user)

        ingredients = (
            RecipeIngredient.objects.filter(recipe__in=recipes)
            .values("ingredient__name", "ingredient__measurement_unit")
            .annotate(total_amount=Sum("amount"))
            .order_by("ingredient__name")
        )

        lines = [
            f"{item['ingredient__name']} ({item['ingredient__measurement_unit']}) — {item['total_amount']}"
            for item in ingredients
        ]
        content = "\n".join(lines)

        response = HttpResponse(content, content_type="text/plain")
        response["Content-Disposition"] = 'attachment; filename="shopping_cart.txt"'
        return response


class UserViewSet(DjoserUserViewSet):
    queryset = User.objects.all()
    permission_classes = [AllowAny]
    pagination_class = StandardResultsSetPagination

    @action(
        detail=False,
        methods=["get"],
        permission_classes=[IsAuthenticated],
        serializer_class=UserSerializer,
        pagination_class=None,
    )
    def me(self, request, *args, **kwargs):
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)

    @action(
        detail=False,
        methods=["get"],
        permission_classes=[IsAuthenticated],
        url_path="subscriptions",
        serializer_class=FollowSerializer,
    )
    def subscriptions(self, request):
        queryset = (
            User.objects.filter(followers__user=request.user)
            .annotate(recipes_count=Count("recipes"))
            .order_by("username")
        )

        page = self.paginate_queryset(queryset)
        serializer = self.get_serializer(page, many=True, context={"request": request})
        return self.get_paginated_response(serializer.data)

    @action(
        detail=True, methods=["post", "delete"], permission_classes=[IsAuthenticated]
    )
    def subscribe(self, request, id=None):
        author = get_object_or_404(User, id=id)

        if request.user == author:
            return Response(
                {"errors": "You cannot subscribe to yourself."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if request.method == "POST":
            if request.user.following.filter(author=author).exists():
                return Response(
                    {"errors": "You are already subscribed to this author."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            Follow.objects.create(user=request.user, author=author)
            serializer = FollowSerializer(author, context={"request": request})
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        if not request.user.following.filter(author=author).exists():
            return Response(
                {"errors": "You are not subscribed to this author."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        request.user.following.filter(author=author).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=False,
        methods=["put"],
        permission_classes=[IsAuthenticated],
        url_path="me/avatar",
        serializer_class=AvatarSerializer,
    )
    def set_avatar(self, request):
        serializer = self.get_serializer(instance=request.user, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)

    @set_avatar.mapping.delete
    def delete_avatar(self, request):
        user = request.user
        if not user.avatar:
            return Response(
                {"errors": "Avatar not set."}, status=status.HTTP_400_BAD_REQUEST
            )
        user.avatar.delete(save=True)
        return Response(status=status.HTTP_204_NO_CONTENT)
