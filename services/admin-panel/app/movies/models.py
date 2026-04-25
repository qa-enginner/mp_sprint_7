from __future__ import annotations

import uuid
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager


class TimeStampedMixin(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class UUIDMixin(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class Meta:
        abstract = True


class Genre(UUIDMixin, TimeStampedMixin):
    name = models.CharField(_('genre'), max_length=255)
    description = models.TextField(_('description'), blank=True)

    def __str__(self):
        return self.name

    class Meta:
        db_table = 'content"."genre'
        verbose_name = _('genre')
        verbose_name_plural = _('genres')
        ordering = ('name',)


class Person(UUIDMixin, TimeStampedMixin):
    full_name = models.CharField(_('name'), max_length=255)

    def __str__(self):
        return self.full_name

    class Meta:
        db_table = 'content"."person'
        verbose_name = _('person')
        verbose_name_plural = _('persons')


class FilmTypes(models.TextChoices):
    MOVIE = 'movie', _('movie')
    TV_SHOW = 'tv show', _('tv show')


class FilmWork(UUIDMixin, TimeStampedMixin):
    title = models.CharField(_('title'), max_length=255)
    description = models.TextField(_('description'), blank=True)
    creation_date = models.DateField(_('creation date'), blank=True)
    rating = models.FloatField(
        _('rating'),
        blank=True,
        validators=[
            MinValueValidator(1.0),
            MaxValueValidator(10.0),
        ],
    )
    type = models.CharField(
        _('type'),
        max_length=7,
        choices=FilmTypes.choices,
        default=FilmTypes.MOVIE,
    )
    genres = models.ManyToManyField(
        Genre,
        through='GenreFilmWork',
        verbose_name=_('genres'),
    )
    persons = models.ManyToManyField(Person, through='PersonFilmWork')

    def __str__(self):
        return self.title

    class Meta:
        db_table = 'content"."film_work'
        verbose_name = _('film')
        verbose_name_plural = _('films')
        ordering = ['-creation_date']
        indexes = [
            models.Index(
                fields=['creation_date', 'rating'],
                name='film_work_creation_rating_idx',
            ),
        ]


class GenreFilmWork(UUIDMixin):
    genre = models.ForeignKey(
        'Genre',
        on_delete=models.CASCADE,
        verbose_name=_('genre'),
    )
    film_work = models.ForeignKey(FilmWork, on_delete=models.CASCADE)
    created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.genre.name

    class Meta:
        db_table = 'content"."genre_film_work'
        verbose_name = _('genre')
        verbose_name_plural = _('film genres')
        constraints = [
            models.UniqueConstraint(
                fields=['film_work', 'genre'],
                name='film_work_genre_idx',
            ),
        ]


class Roles(models.TextChoices):
    ACTOR = 'actor', _('actor')
    DIRECTOR = 'director', _('director')
    WRITER = 'writer', _('writer')


class PersonFilmWork(UUIDMixin):
    person = models.ForeignKey(
        'Person',
        on_delete=models.CASCADE,
        verbose_name=_('person'),
    )
    film_work = models.ForeignKey(FilmWork, on_delete=models.CASCADE)
    role = models.CharField(
        _('role'),
        max_length=10,
        choices=Roles.choices,
        default=Roles.ACTOR,
    )
    created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.person.full_name

    class Meta:
        db_table = 'content"."person_film_work'
        verbose_name = _('person')
        verbose_name_plural = _('film persons')
        constraints = [
            models.UniqueConstraint(
                fields=['film_work', 'person', 'role'],
                name='film_work_person_role_idx',
            ),
        ]


class MyUserManager(BaseUserManager):
    def create_user(self, email, password=None):
        if not email:
            raise ValueError('Users must have an email address')

        user = self.model(email=self.normalize_email(email))
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None):
        user = self.create_user(email, password=password)
        user.is_admin = True
        user.save(using=self._db)
        return user


class User(AbstractBaseUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(verbose_name='email address', max_length=255, unique=True)
    is_active = models.BooleanField(default=True)
    is_admin = models.BooleanField(default=False)
    first_name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255)

    # строка с именем поля модели, которая используется в качестве уникального идентификатора
    USERNAME_FIELD = 'email'

    # менеджер модели
    objects = MyUserManager()

    def __str__(self):
        return f'{self.email} {self.id}'

    def has_perm(self, perm, obj=None):
        return True

    def has_module_perms(self, app_label):
        return True