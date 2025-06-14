from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.validators import RegexValidator


class User(AbstractUser):

    email = models.EmailField(
        max_length=254,
        unique=True,
        verbose_name='Email Address',
    )
    username = models.CharField(
        max_length=150,
        unique=True,
        verbose_name='Username',
        validators=[
                RegexValidator(
                    regex=r'^[\w.@+-]+$',
                    message='Недопустимое имя пользователя.'
                )
            ]
    )
    first_name = models.CharField(
        max_length=150,
        verbose_name='First Name',
    )
    last_name = models.CharField(
        max_length=150,
        verbose_name='Last Name',
    )
    avatar = models.ImageField(
        upload_to='accounts/avatars/',
        blank=True,
        null=True,
        verbose_name='Avatar'
    )

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']

    class Meta:
        ordering = ['email']
        verbose_name = 'User'
        verbose_name_plural = 'Users'

    def __str__(self):
        return self.username

class Follow(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='following',
        verbose_name='Follower',
    )
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='followers',
        verbose_name='Author',
    )

    class Meta:
        verbose_name = 'Follow'
        verbose_name_plural = 'Follows'
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'author'],
                name='unique_follow_constraint',
            ),
            models.CheckConstraint(
                check=~models.Q(user=models.F('author')),
                name='prevent_self_follow',
            ),
        ]

    def __str__(self):
        return f'{self.user} follows {self.author}'
