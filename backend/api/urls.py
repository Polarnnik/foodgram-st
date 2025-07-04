from django.urls import include, path
from rest_framework.routers import DefaultRouter
from .views import IngredientViewSet, RecipeViewSet, UserViewSet


router = DefaultRouter()
router.register("ingredients", IngredientViewSet, basename="ingredients")
router.register("recipes", RecipeViewSet, basename="recipes")
router.register("users", UserViewSet, basename="users")

urlpatterns = [
    path("", include(router.urls)),
    path("auth/", include("djoser.urls.authtoken")),
]
