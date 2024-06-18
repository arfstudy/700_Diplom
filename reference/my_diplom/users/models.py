from django.contrib.auth.models import AbstractUser, UserManager
from django.core.validators import EmailValidator
from django.db import models


class AppUserManager(UserManager):
    """ Диспетчер записей для создания пользователя по электронной почте и без ника (username).
    """
    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        """ Create and save a user with the given email and password.
        """
        if not email:
            raise ValueError('The given email must be set')    # Указанный адрес электронной почты должен быть задан.
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email=None, password=None, **extra_fields):
        """ Создаёт нового пользователя.
        """
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email=None, password=None, **extra_fields):
        """ Создаёт нового суперпользователя.
        """
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        extra_fields['is_active'] = True

        return self._create_user(email, password, **extra_fields)


class User(AbstractUser):
    """ Пользователь.
    """
    class UserType(models.TextChoices):
        """ Должность - (Тип пользователя). """
        SALES = 'SL', 'Менеджер по продажам'    # "Закупка товара не входит в ваши обязанности".
        BUYER = 'BR', 'Менеджер по закупкам'    # "Продажа товара не входит в ваши обязанности".

    email_validator = EmailValidator()

    # Ваше имя должно содержать только русские или только латинские буквы.
    # validators.NameValidator()

    # Поле, через которое будет происходить аутентификация пользователя.
    USERNAME_FIELD = 'email'
    # Список полей, которые запрашиваются при создании пользователя в консоле (createsuperuser).
    # Поле 'email' добавлять сюда не требуется, оно обязательное.
    REQUIRED_FIELDS = []

    username = None    # Поле 'username' в проекте не используется.
    email = models.EmailField(
        unique=True,
        validators=[email_validator],
        verbose_name='Электронная почта'
    )
    email_verify = models.BooleanField(default=False, verbose_name='Подтверждённая почта')
    company = models.CharField(max_length=40, null=True, blank=True, verbose_name='Компания')
    position = models.CharField(
        max_length=2,
        null=True, blank=True,
        choices=UserType.choices,
        verbose_name='Должность'  # (Тип пользователя).
    )
    is_active = models.BooleanField(
        default=False,
        verbose_name='Действующий',
        help_text=(
            "Указывает, следует ли считать этого пользователя активным."
            "Снимите этот флажок вместо удаления учётной записи."
        ),
    )

    persons = AppUserManager()

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'
        ordering = ['last_name', 'first_name']

    def __str__(self):
        return f'{self.id}: {self.first_name} {self.last_name}, ({self.email})'

    def get_full_state(self):
        """ Возвращает имя, компанию, должность и электронный адрес пользователя.
        """
        return (f'{self.id}: {self.first_name} {self.last_name}, {self.company}'
                f', `{self.get_position_display()}` ({self.email})')
