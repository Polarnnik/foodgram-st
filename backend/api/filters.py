from django_filters.rest_framework import FilterSet, AllValuesMultipleFilter
from django_filters import rest_framework as filters
from recipes.models import Recipe, Ingredient


class RecipeFilter(FilterSet):
    is_favorited = filters.BooleanFilter(method="filter_is_favorited")
    is_in_shopping_cart = filters.BooleanFilter(method="filter_is_in_shopping_cart")

    class Meta:
        model = Recipe
        fields = ("author", "is_favorited", "is_in_shopping_cart")

    def filter_is_favorited(self, queryset, name, value):
        user = self.request.user
        if value and user.is_authenticated:
            return queryset.filter(favorite_relations__user=user)
        return queryset

    def filter_is_in_shopping_cart(self, queryset, name, value):
        user = self.request.user
        if value and user.is_authenticated:
            return queryset.filter(shopping_cart__user=user)
        return queryset


class IngredientFilter(FilterSet):

    class Meta:
        model = Ingredient
        fields = [
            "name",
        ]
