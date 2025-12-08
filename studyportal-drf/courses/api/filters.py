import django_filters

from courses.models import Course


class CourseFilter(django_filters.FilterSet):
    """
    Advanced filtering for courses

    Filters:
    - category: Filter by category UUID
    - status: Filter by course status
    - search: Search in title, code, description
    - has_space: Filter courses with available space
    """

    title = django_filters.CharFilter(lookup_expr='icontains')
    category = django_filters.UUIDFilter(field_name='categories__id')
    status = django_filters.ChoiceFilter(choices=Course.STATUS_CHOICES)
    has_space = django_filters.BooleanFilter(method='filter_has_space')

    class Meta:
        model = Course
        fields = ['status', 'is_active', 'category']

    def filter_has_space(self, queryset, name, value):
        """Filter courses that have available space"""
        if value:
            from django.db.models import F, Q

            return queryset.filter(
                Q(max_students__isnull=True) | Q(max_students__gt=F('enrollments__count'))
            ).distinct()
        return queryset
