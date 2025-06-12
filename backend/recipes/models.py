from django.db import models

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
