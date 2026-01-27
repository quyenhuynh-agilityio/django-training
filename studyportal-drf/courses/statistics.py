"""
Course statistics aggregation for dashboard and analytics.
Uses Django caching to avoid recalculating on every request.
"""

from datetime import timedelta

from django.db.models import Avg, Count, Q
from django.utils import timezone

from core.cache import build_cache_key, cache_get_or_set, delete_cache_with_prefix, get_timeout
from courses.models import Course
from enrollments.models import Enrollment


def get_statistics_cache_timeout():
    """
    Get cache timeout from settings. Defaults to 30 seconds.
    Admin can override this in settings.py:
    STATISTICS_CACHE_TIMEOUT = 60  # seconds
    """
    return get_timeout('STATISTICS_CACHE_TIMEOUT', 30)


class CourseStatistics:
    """
    Computes dynamic statistics about courses and enrollments.
    Used for: Admin dashboard, analytics API, instructor insights.

    All methods use Django cache to prevent repeated DB queries.
    Cache invalidation happens automatically based on timeout.
    """

    CACHE_KEY_PREFIX = 'course_stats'

    @classmethod
    def _get_cache_key(cls, stat_type, **kwargs):
        """Generate unique cache key based on stat type and parameters."""
        return build_cache_key(cls.CACHE_KEY_PREFIX, stat=stat_type, **kwargs)

    @classmethod
    def get_average_enrollments(cls, time_period=None):
        """
        Calculate average number of enrollments per course.
        Result is cached for STATISTICS_CACHE_TIMEOUT seconds.

        Args:
            time_period (int, optional): Number of days to look back.
                                        None = all time.

        Returns:
            dict: {
                'average': float,
                'total_courses': int,
                'total_enrollments': int
            }
        """
        cache_key = cls._get_cache_key('avg_enrollments', days=time_period)

        def compute():
            queryset = Course.objects.filter(is_active=True)

            # Filter enrollments by time period if specified
            enrollment_filter = Q(enrollments__is_active=True)
            if time_period:
                since = timezone.now() - timedelta(days=time_period)
                enrollment_filter &= Q(enrollments__created_at__gte=since)

            stats = queryset.annotate(
                enrollment_count=Count('enrollments', filter=enrollment_filter)
            ).aggregate(
                average=Avg('enrollment_count'),
                total_courses=Count('id'),
                total_enrollments=Count('enrollments', filter=enrollment_filter),
            )

            return {
                'average': round(stats['average'] or 0, 2),
                'total_courses': stats['total_courses'],
                'total_enrollments': stats['total_enrollments'],
            }

        return cache_get_or_set(cache_key, compute, timeout=get_statistics_cache_timeout())

    @classmethod
    def get_top_courses(cls, limit=10, time_period=None):
        """
        Get courses with the most enrollments.
        Result is cached for STATISTICS_CACHE_TIMEOUT seconds.

        Args:
            limit (int): Number of top courses to return
            time_period (int, optional): Days to look back. None = all time.

        Returns:
            list: List of Course objects annotated with enrollment_count
        """
        cache_key = cls._get_cache_key('top_courses', limit=limit, days=time_period)

        def compute():
            queryset = Course.objects.filter(is_active=True)

            enrollment_filter = Q(enrollments__is_active=True)
            if time_period:
                since = timezone.now() - timedelta(days=time_period)
                enrollment_filter &= Q(enrollments__created_at__gte=since)

            result = queryset.annotate(
                enrollment_count=Count('enrollments', filter=enrollment_filter)
            ).order_by('-enrollment_count')[:limit]

            # Cache the queryset (convert to list for caching)
            return list(result)

        return cache_get_or_set(cache_key, compute, timeout=get_statistics_cache_timeout())

    @classmethod
    def get_enrollment_trends(cls, days=30):
        """
        Get daily enrollment counts for trend analysis.
        Result is cached for STATISTICS_CACHE_TIMEOUT seconds.

        Args:
            days (int): Number of days to analyze

        Returns:
            list: [{date, count}, ...] for the last N days
        """
        cache_key = cls._get_cache_key('enrollment_trends', days=days)

        def compute():
            from django.db.models.functions import TruncDate

            since = timezone.now() - timedelta(days=days)

            daily_enrollments = (
                Enrollment.objects.filter(created_at__gte=since, is_active=True)
                .annotate(date=TruncDate('created_at'))
                .values('date')
                .annotate(count=Count('id'))
                .order_by('date')
            )

            return list(daily_enrollments)

        return cache_get_or_set(cache_key, compute, timeout=get_statistics_cache_timeout())

    @classmethod
    def clear_all_cache(cls):
        """
        Manually clear all statistics cache.
        Useful when you want to force recalculation (e.g., after bulk updates).
        """
        delete_cache_with_prefix(build_cache_key(cls.CACHE_KEY_PREFIX))
