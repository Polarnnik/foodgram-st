from django.db import models
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db.models import Exists, OuterRef, Manager, Value, BooleanField
from users.models import User
from django.conf import settings
from django.urls import reverse

# Константы
MIN_AMOUNT = 1
MAX_AMOUNT = 32_000
MIN_COOKING_TIME = 1
MAX_COOKING_TIME = 32_000


class Ingredient(models.Model):
    name = models.CharField(
        max_length=200,
        verbose_name="Ingredient",
    )
    measurement_unit = models.CharField(
        max_length=50,
        verbose_name="Measurement Unit",
    )

    class Meta:
        verbose_name = "Ingredient"
        verbose_name_plural = "Ingredients"
        ordering = ["name"]

        constraints = [
            models.UniqueConstraint(
                fields=["name", "measurement_unit"],
                name="unique_ingredient_unit",
            ),
        ]

    def __str__(self):
        return f"{self.name} ({self.measurement_unit})"


class RecipeManager(Manager):
    def with_user_annotations(self, user):
        queryset = self.get_queryset()
        if user and user.is_authenticated:
            return queryset.annotate(
                is_favorited=Exists(
                    Favorite.objects.filter(user=user, recipe=OuterRef("pk"))
                ),
                is_in_shopping_cart=Exists(
                    ShoppingCart.objects.filter(user=user, recipe=OuterRef("pk"))
                ),
            )
        return queryset.annotate(
            is_favorited=Value(False, output_field=BooleanField()),
            is_in_shopping_cart=Value(False, output_field=BooleanField()),
        )


class Recipe(models.Model):
    objects = RecipeManager()
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="recipes",
        verbose_name="Author",
    )
    name = models.CharField(
        max_length=200,
        verbose_name="Recipe name",
    )
    text = models.TextField(verbose_name="Description")
    image = models.ImageField(
        upload_to="recipes/images/",
        verbose_name="Image",
    )
    cooking_time = models.PositiveSmallIntegerField(
        verbose_name="Cooking Time (minutes)",
        validators=[
            MinValueValidator(
                MIN_COOKING_TIME, message="Time must be at least 1 minute."
            ),
            MaxValueValidator(
                MAX_COOKING_TIME, message="Time cannot exceed 32,000 minutes."
            ),
        ],
    )
    ingredients = models.ManyToManyField(
        Ingredient,
        through="RecipeIngredient",
        related_name="recipes",
        verbose_name="Ingredients",
    )
    pub_date = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Publication Date",
    )

    class Meta:
        ordering = ["-pub_date"]
        verbose_name = "Recipe"
        verbose_name_plural = "Recipes"

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("api:recipe-detail", kwargs={"pk": self.pk})


class RecipeIngredient(models.Model):
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name="recipe_ingredients",
        verbose_name="Recipe",
    )
    ingredient = models.ForeignKey(
        Ingredient,
        on_delete=models.CASCADE,
        related_name="ingredient_recipes",
        verbose_name="Ingredient",
    )
    amount = models.PositiveSmallIntegerField(
        verbose_name="Amount",
        validators=[
            MinValueValidator(MIN_AMOUNT, message="Amount must be at least 1."),
            MaxValueValidator(MAX_AMOUNT, message="Amount cannot exceed 32,000."),
        ],
    )

    class Meta:
        verbose_name = "Recipe Ingredient"
        verbose_name_plural = "Recipe Ingredients"
        ordering = ["ingredient__name"]
        constraints = [
            models.UniqueConstraint(
                fields=["recipe", "ingredient"],
                name="unique_recipe_ingredient",
            ),
        ]

    def __str__(self):
        return f"{self.ingredient} in {self.recipe}"


class UserRecipeRelation(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="%(class)s_relations",
        verbose_name="User",
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name="%(class)s_relations",
        verbose_name="Recipe",
    )

    class Meta:
        abstract = True
        ordering = ["user", "recipe"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "recipe"],
                name="%(app_label)s_%(class)s_unique_relation",
            )
        ]

    def __str__(self):
        return f"{self.__class__.__name__}: {self.user.username} <> {self.recipe.name}"


class Favorite(UserRecipeRelation):
    class Meta(UserRecipeRelation.Meta):
        verbose_name = "Favorite"
        verbose_name_plural = "Favorites"


class ShoppingCart(UserRecipeRelation):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="shopping_cart"
    )
    recipe = models.ForeignKey(
        Recipe, on_delete=models.CASCADE, related_name="shopping_cart"
    )

    class Meta(UserRecipeRelation.Meta):
        verbose_name = "Shopping Cart Item"
        verbose_name_plural = "Shopping Cart Items"

    def __str__(self):
        return f"ShoppingCart: {self.user.username} <> {self.recipe.name}"
