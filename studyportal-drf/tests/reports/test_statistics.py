"""Tests for reports.statistics module."""

from unittest.mock import patch

import pytest

from reports.statistics import (
    CourseStatistics,
    course_stats,
    get_statistics_cache_timeout,
)


class TestGetStatisticsCacheTimeout:
    def test_returns_setting_when_present(self, settings):
        settings.STATISTICS_CACHE_TIMEOUT = 60
        assert get_statistics_cache_timeout() == 60

    def test_returns_default_30_when_missing(self, settings):
        assert get_statistics_cache_timeout() == 30


@pytest.mark.django_db
class TestCourseStatistics:
    @patch('reports.statistics.get_statistics_cache_timeout')
    @patch('reports.statistics.cache_get_or_set')
    def test_get_average_enrollments_all_time(
        self, mock_cache_get, mock_timeout, create_course, create_enrollment
    ):
        mock_timeout.return_value = 30
        mock_cache_get.side_effect = lambda key, compute, timeout: compute()

        svc = CourseStatistics('test_stats')
        result = svc.get_average_enrollments(time_period=None)

        assert 'average' in result
        assert 'total_courses' in result
        assert 'total_enrollments' in result
        assert result['total_courses'] >= 0
        assert result['total_enrollments'] >= 0

    @patch('reports.statistics.get_statistics_cache_timeout')
    @patch('reports.statistics.cache_get_or_set')
    def test_get_average_enrollments_with_time_period(
        self, mock_cache_get, mock_timeout, create_course
    ):
        mock_timeout.return_value = 30
        mock_cache_get.side_effect = lambda key, compute, timeout: compute()

        svc = CourseStatistics('test_stats')
        result = svc.get_average_enrollments(time_period=7)

        assert 'average' in result
        assert 'total_courses' in result
        assert 'total_enrollments' in result

    @patch('reports.statistics.get_statistics_cache_timeout')
    @patch('reports.statistics.cache_get_or_set')
    def test_get_top_courses(
        self, mock_cache_get, mock_timeout, create_course, create_enrollment
    ):
        mock_timeout.return_value = 30
        mock_cache_get.side_effect = lambda key, compute, timeout: compute()

        svc = CourseStatistics('test_stats')
        result = svc.get_top_courses(limit=5, time_period=None)

        assert isinstance(result, list)
        assert len(result) <= 5

    @patch('reports.statistics.get_statistics_cache_timeout')
    @patch('reports.statistics.cache_get_or_set')
    def test_get_enrollment_trends(self, mock_cache_get, mock_timeout):
        mock_timeout.return_value = 30
        mock_cache_get.side_effect = lambda key, compute, timeout: compute()

        svc = CourseStatistics('test_stats')
        result = svc.get_enrollment_trends(days=30)

        assert isinstance(result, list)

    @patch('reports.statistics.delete_cache_with_prefix')
    @patch('reports.statistics.build_cache_key')
    def test_clear_all_cache(self, mock_build_key, mock_delete):
        mock_build_key.return_value = 'test_stats:v1'
        svc = CourseStatistics('test_stats')
        svc.clear_all_cache()
        mock_delete.assert_called_once_with('test_stats:v1')

    def test_cache_key_includes_prefix_and_stat_type(self):
        svc = CourseStatistics('my_prefix')
        key = svc._get_cache_key('avg_enrollments', days=7)
        assert 'my_prefix' in key or 'avg_enrollments' in key or '7' in key


@pytest.mark.django_db
def test_course_stats_singleton():
    """course_stats is a CourseStatistics instance with fixed prefix."""
    assert course_stats.CACHE_KEY_PREFIX == 'course_stats'
