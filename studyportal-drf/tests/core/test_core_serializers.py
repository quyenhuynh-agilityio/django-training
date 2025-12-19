from django.test import TestCase

from utils.serializers import camel_to_snake, snake_to_camel, transform_keys


class CaseConversionTests(TestCase):
    """Tests for case conversion utilities."""

    def test_snake_to_camel_basic(self):
        """Test basic snake_case to camelCase conversion."""
        self.assertEqual(snake_to_camel('first_name'), 'firstName')
        self.assertEqual(snake_to_camel('last_name'), 'lastName')
        self.assertEqual(snake_to_camel('date_of_birth'), 'dateOfBirth')

    def test_snake_to_camel_no_underscore(self):
        """Test strings without underscores remain unchanged."""
        self.assertEqual(snake_to_camel('id'), 'id')
        self.assertEqual(snake_to_camel('email'), 'email')
        self.assertEqual(snake_to_camel('name'), 'name')

    def test_snake_to_camel_empty(self):
        """Test empty string handling."""
        self.assertEqual(snake_to_camel(''), '')

    def test_camel_to_snake_basic(self):
        """Test basic camelCase to snake_case conversion."""
        self.assertEqual(camel_to_snake('firstName'), 'first_name')
        self.assertEqual(camel_to_snake('lastName'), 'last_name')
        self.assertEqual(camel_to_snake('dateOfBirth'), 'date_of_birth')

    def test_camel_to_snake_pascal_case(self):
        """Test PascalCase to snake_case conversion."""
        self.assertEqual(camel_to_snake('UserProfile'), 'user_profile')
        self.assertEqual(camel_to_snake('HTTPResponse'), 'http_response')

    def test_camel_to_snake_no_uppercase(self):
        """Test strings without uppercase remain unchanged."""
        self.assertEqual(camel_to_snake('id'), 'id')
        self.assertEqual(camel_to_snake('email'), 'email')

    def test_camel_to_snake_empty(self):
        """Test empty string handling."""
        self.assertEqual(camel_to_snake(''), '')

    def test_transform_keys_nested_dict(self):
        """Test transformation of nested dictionaries."""
        data = {
            'user_name': 'John',
            'user_profile': {'date_of_birth': '1990-01-01', 'is_active': True},
        }
        result = transform_keys(data, snake_to_camel)

        self.assertEqual(result['userName'], 'John')
        self.assertEqual(result['userProfile']['dateOfBirth'], '1990-01-01')
        self.assertEqual(result['userProfile']['isActive'], True)

    def test_transform_keys_list(self):
        """Test transformation of lists."""
        data = [
            {'first_name': 'John', 'last_name': 'Doe'},
            {'first_name': 'Jane', 'last_name': 'Smith'},
        ]
        result = transform_keys(data, snake_to_camel)

        self.assertEqual(result[0]['firstName'], 'John')
        self.assertEqual(result[1]['lastName'], 'Smith')

    def test_transform_keys_mixed(self):
        """Test transformation of mixed nested structures."""
        data = {
            'course_list': [
                {'course_name': 'Python', 'course_code': 'CS101'},
                {'course_name': 'Django', 'course_code': 'CS102'},
            ],
            'total_count': 2,
        }
        result = transform_keys(data, snake_to_camel)

        self.assertEqual(result['courseList'][0]['courseName'], 'Python')
        self.assertEqual(result['courseList'][1]['courseCode'], 'CS102')
        self.assertEqual(result['totalCount'], 2)
