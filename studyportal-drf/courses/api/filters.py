import django_filters

from courses.models import Course


class CourseFilter(django_filters.FilterSet):
    """
    Advanced filtering for courses

    Filters:
    - title: Filter by course title/name (case-insensitive partial match)
    - category: Filter by category UUID
    - status: Filter by course status
    - search: Search in title, code, description (via SearchFilter)
    """

    title = django_filters.CharFilter(
        lookup_expr='icontains', help_text='Filter by course title/name'
    )
    category = django_filters.UUIDFilter(field_name='categories__id')
    status = django_filters.ChoiceFilter(choices=Course.STATUS_CHOICES)

    class Meta:
        model = Course
        fields = ['status', 'is_active', 'category', 'title']
