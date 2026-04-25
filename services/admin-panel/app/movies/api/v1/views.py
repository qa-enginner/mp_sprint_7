"""Movie API Views.

This module contains the API views for the movies application.
It provides endpoints for listing movies and retrieving detailed
information about specific movies.
"""

from django.contrib.postgres.aggregates import ArrayAgg
from django.db.models import Q
from django.http import JsonResponse
from django.views.generic.list import BaseListView
from django.views.generic.detail import BaseDetailView
from django.db.models.query import QuerySet

from movies.models import FilmWork


class MoviesApiMixin:
    """Mixin class for movie API views.

    Provides common functionality for movie-related API views including
    database query operations and JSON response formatting.
    """
    model = FilmWork
    http_method_names = ['get']  # Список методов, которые реализует обработчик

    def get_queryset(self) -> QuerySet[FilmWork]:
        """Get the queryset for film works with related data.

        Returns:
            QuerySet: A queryset of FilmWork objects with annotated fields
                     including genres and persons grouped by role.
        """
        queryset = FilmWork.objects.values(
            'id',
            'title',
            'description',
            'creation_date',
            'rating',
            'type').annotate(
            genres=ArrayAgg('genres__name', distinct=True),
            actors=ArrayAgg(
                'persons__full_name',
                distinct=True,
                filter=Q(personfilmwork__role='actor'),
                default=['no data']
            ),
            directors=ArrayAgg(
                'persons__full_name',
                distinct=True,
                filter=Q(personfilmwork__role='director'),
                default=['no data']
            ),
            writers=ArrayAgg(
                'persons__full_name',
                distinct=True,
                filter=Q(personfilmwork__role='writer'),
                default=['no data']
            )
        )

        return queryset

    def render_to_response(self, context, **response_kwargs) -> JsonResponse:
        """Render the response as JSON.

        Args:
            context (dict): The context data to be serialized.
            **response_kwargs: Additional keyword arguments for the response.

        Returns:
            JsonResponse: The context data serialized as JSON.
        """
        return JsonResponse(context)


class MoviesListApi(MoviesApiMixin, BaseListView):
    """API view for listing movies.

    Provides a paginated list of movies with related data.
    Inherits from MoviesApiMixin for common functionality.
    """
    paginate_by = 50

    def get_context_data(self, **kwargs) -> dict[str, any]:
        """Get context data for the movies list.

        Args:
            object_list: The list of objects to display (optional).
            **kwargs: Additional keyword arguments.

        Returns:
            dict: Context data including pagination information and results.
        """
        queryset = self.get_queryset()
        paginator, page, queryset, is_paginated = self.paginate_queryset(
            queryset, self.paginate_by
        )
        context = {
            'count': paginator.count,
            'total_pages': paginator.num_pages,
            'prev': (
                page.previous_page_number() if page.has_previous() else None
            ),
            'next': page.next_page_number() if page.has_next() else None,
            'results': list(queryset),
        }
        return context


class MoviesDetailApi(MoviesApiMixin, BaseDetailView):
    """API view for retrieving details of a specific movie.

    Provides detailed information for a single movie identified by its ID.
    Inherits from MoviesApiMixin for common functionality.
    """
    def get_context_data(self, **kwargs) -> dict[str, any]:
        """Get context data for a specific movie.

        Args:
            **kwargs: Additional keyword arguments.

        Returns:
            dict: Context data for the specified movie.
        """
        context = super().get_context_data()['object']
        return context
