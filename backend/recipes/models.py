from django.db import models
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db.models import Exists, OuterRef, Manager
from users.models import User
from django.conf import settings

class Tag(models.Model):
    name = models.CharField(
        max_length=200,
        unique=True,
        verbose_name='Tag Name',
    )
    slug = models.SlugField(
        max_length=200,
        unique=True,
        verbose_name='Slug',
    )

    class Meta:
        verbose_name = 'Tag'
        verbose_name_plural = 'Tags'
        ordering = ['name']

    def __str__(self):
        return self.name

class Ingredient(models.Model):
    name = models.CharField(
        max_length=200,
        verbose_name='Ingredient',
    )
    measurement_unit = models.CharField(
        max_length=50,
        verbose_name='Measurement Unit',
    )

    class Meta:
        verbose_name = 'Ingredient'
        verbose_name_plural = 'Ingredients'
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(
                fields=['name', 'measurement_unit'],
                name='unique_ingredient_unit',
            ),
        ]

    def __str__(self):
        return f'{self.name} ({self.measurement_unit})'

class RecipeManager(Manager):
    def with_user_annotations(self, user):
        queryset = self.get_queryset()
        if user and user.is_authenticated:
            return queryset.annotate(
                is_favorited=Exists(
                    Favorite.objects.filter(user=user, recipe=OuterRef('pk'))
                ),
                is_in_shopping_cart=Exists(
                    ShoppingCart.objects.filter(user=user, recipe=OuterRef('pk'))
                )
            )
        return queryset.annotate(
            is_favorited=models.Value(False, output_field=models.BooleanField()),
            is_in_shopping_cart=models.Value(False, output_field=models.BooleanField())
        )

class Recipe(models.Model):
    objects = RecipeManager()
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='recipes',
        verbose_name='Author',
    )
    name = models.CharField(
        max_length=200,
        verbose_name='Recipe name',
    )
    text = models.TextField(verbose_name='Description')
    image = models.ImageField(
        upload_to='recipes/images/',
        verbose_name='Image',
    )
    cooking_time = models.PositiveSmallIntegerField(
        verbose_name='Cooking Time (minutes)',
        validators=[
            MinValueValidator(1, message='Time must be at least 1 minute.'),
            MaxValueValidator(1440, message='Time cannot exceed 1440 minutes.'),
        ],
    )
    tags = models.ManyToManyField(
        Tag,
        related_name='recipes',
        verbose_name='Tags',
    )
    ingredients = models.ManyToManyField(
        Ingredient,
        through='RecipeIngredient',
        related_name='recipes',
        verbose_name='Ingredients',
    )
    pub_date = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Publication Date',
    )

    class Meta:
        ordering = ['-pub_date']
        verbose_name = 'Recipe'
        verbose_name_plural = 'Recipes'

    def get_absolute_url(self):
        return reverse('api:recipe-detail', kwargs={'pk': self.pk})

    def __str__(self):
        return self.name

class RecipeIngredient(models.Model):
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name='recipe_ingredients',
        verbose_name='Recipe',
    )
    ingredient = models.ForeignKey(
        Ingredient,
        on_delete=models.CASCADE,
        related_name='ingredient_recipes',
        verbose_name='Ingredient',
    )
    amount = models.PositiveSmallIntegerField(
        verbose_name='Amount',
        validators=[
            MinValueValidator(1, message='Amount must be at least 1.'),
        ],
    )

    class Meta:
        verbose_name = 'Recipe Ingredient'
        verbose_name_plural = 'Recipe Ingredients'
        constraints = [
            models.UniqueConstraint(
                fields=['recipe', 'ingredient'],
                name='unique_recipe_ingredient',
            ),
        ]

    def __str__(self):
        return f'{self.ingredient} in {self.recipe}'

class UserRecipeRelation(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='%(class)s_relations',
        verbose_name='User',
    )
    recipe = models.ForeignKey(
        'Recipe',
        on_delete=models.CASCADE,
        related_name='%(class)s_relations',
        verbose_name='Recipe',
    )

    class Meta:
        abstract = True
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'recipe'],
                name='%(app_label)s_%(class)s_unique_relation'
            )
        ]

    def __str__(self):
        return f'{self.__class__.__name__}: {self.user.username} <> {self.recipe.name}'

class Favorite(UserRecipeRelation):
    class Meta(UserRecipeRelation.Meta):
        verbose_name = 'Favorite'
        verbose_name_plural = 'Favorites'

class ShoppingCart(UserRecipeRelation):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='shopping_cart')
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE, related_name='shopping_cart')

    class Meta(UserRecipeRelation.Meta):
        verbose_name = 'Shopping Cart Item'
        verbose_name_plural = 'Shopping Cart Items'
