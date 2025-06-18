from rest_framework import serializers
from django.contrib.auth import get_user_model
from drf_extra_fields.fields import Base64ImageField
from django.db import transaction

from recipes.models import (
    Ingredient,
    RecipeIngredient,
    Recipe,
    Favorite,
    ShoppingCart,
)

User = get_user_model()

# Константы
MIN_AMOUNT = 1
MAX_AMOUNT = 32_000
MIN_COOKING_TIME = 1
MAX_COOKING_TIME = 32_000


class IngredientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ingredient
        fields = ("id", "name", "measurement_unit")


class AvatarSerializer(serializers.ModelSerializer):
    avatar = Base64ImageField(required=True)

    class Meta:
        model = User
        fields = ("avatar",)


class UserSerializer(serializers.ModelSerializer):
    is_subscribed = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "username",
            "first_name",
            "last_name",
            "avatar",
            "is_subscribed",
        )

    def get_is_subscribed(self, obj):
        request = self.context.get("request")
        if not request or request.user.is_anonymous:
            return False
        return obj.followers.filter(user=request.user).exists()


class RecipeIngredientReadSerializer(serializers.ModelSerializer):
    id = serializers.ReadOnlyField(source="ingredient.id")
    name = serializers.ReadOnlyField(source="ingredient.name")
    measurement_unit = serializers.ReadOnlyField(source="ingredient.measurement_unit")

    class Meta:
        model = RecipeIngredient
        fields = ("id", "name", "measurement_unit", "amount")


class RecipeMiniSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = ("id", "name", "image", "cooking_time")

    def get_image(self, obj):
        return obj.image.url if obj.image else ""


class RecipeReadSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)
    ingredients = RecipeIngredientReadSerializer(
        source="recipe_ingredients", many=True, read_only=True
    )
    is_favorited = serializers.BooleanField(read_only=True)
    is_in_shopping_cart = serializers.BooleanField(read_only=True)
    image = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = (
            "id",
            "author",
            "ingredients",
            "is_favorited",
            "is_in_shopping_cart",
            "name",
            "image",
            "text",
            "cooking_time",
        )

    def get_image(self, obj):
        return obj.image.url if obj.image else ""


class RecipeIngredientWriteSerializer(serializers.ModelSerializer):
    id = serializers.PrimaryKeyRelatedField(
        queryset=Ingredient.objects.all(), source="ingredient"
    )
    amount = serializers.IntegerField(min_value=MIN_AMOUNT, max_value=MAX_AMOUNT)

    class Meta:
        model = RecipeIngredient
        fields = ("id", "amount")


class RecipeWriteSerializer(serializers.ModelSerializer):
    ingredients = RecipeIngredientWriteSerializer(many=True, allow_empty=False)
    image = Base64ImageField()
    cooking_time = serializers.IntegerField(
        min_value=MIN_COOKING_TIME, max_value=MAX_COOKING_TIME
    )

    class Meta:
        model = Recipe
        fields = ("ingredients", "image", "name", "text", "cooking_time")

    def validate_ingredients(self, value):
        ingredient_ids = [item["ingredient"].id for item in value]
        if len(ingredient_ids) != len(set(ingredient_ids)):
            raise serializers.ValidationError("Ingredients must be unique.")
        return value

    def validate_image(self, value):
        if value in (None, ""):
            raise serializers.ValidationError("Image field may not be empty.")
        return value

    def create_ingredients(self, recipe, ingredients_data):
        RecipeIngredient.objects.bulk_create(
            [
                RecipeIngredient(
                    recipe=recipe, ingredient=item["ingredient"], amount=item["amount"]
                )
                for item in ingredients_data
            ]
        )

    @transaction.atomic
    def create(self, validated_data):
        ingredients = validated_data.pop("ingredients")
        user = self.context["request"].user
        recipe = Recipe.objects.create(author=user, **validated_data)
        self.create_ingredients(recipe, ingredients)

        recipe = Recipe.objects.with_user_annotations(user).get(pk=recipe.pk)

        return recipe

    @transaction.atomic
    def update(self, instance, validated_data):
        request = self.context.get("request")
        is_partial = request and request.method == "PATCH"

        if is_partial and "ingredients" not in self.initial_data:
            raise serializers.ValidationError(
                {"ingredients": "This field is required."}
            )

        ingredients = validated_data.pop("ingredients", None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        if ingredients is not None:
            instance.recipe_ingredients.all().delete()
            self.create_ingredients(instance, ingredients)

        instance.save()

        user = request.user
        instance.is_favorited = instance.favorite_relations.filter(user=user).exists()
        instance.is_in_shopping_cart = instance.shopping_cart.filter(user=user).exists()

        return instance

    def to_representation(self, instance):
        return RecipeReadSerializer(instance, context=self.context).data


class FollowSerializer(UserSerializer):
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.IntegerField(source="recipes.count", read_only=True)

    class Meta(UserSerializer.Meta):
        fields = UserSerializer.Meta.fields + ("recipes", "recipes_count")

    def get_recipes(self, obj):
        request = self.context.get("request")
        limit = request.query_params.get("recipes_limit")
        queryset = obj.recipes.all()
        if limit and limit.isdigit():
            queryset = queryset[: int(limit)]
        return RecipeMiniSerializer(queryset, many=True, context=self.context).data
