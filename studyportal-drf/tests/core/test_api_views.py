from rest_framework.permissions import IsAuthenticated

from core.api_views import CommonViewSet


def test_get_permissions_uses_map_when_defined():
    """When permission_classes_map is set, get_permissions returns action-based permissions."""
    class ViewSet(CommonViewSet):
        permission_classes = [IsAuthenticated]
        permission_classes_map = {
            'list': [],
            'create': [IsAuthenticated],
        }

    viewset = ViewSet()
    viewset.action = 'list'
    perms = viewset.get_permissions()
    assert len(perms) == 0

    viewset.action = 'create'
    perms = viewset.get_permissions()
    assert len(perms) == 1

    viewset.action = 'unknown'
    perms = viewset.get_permissions()
    assert len(perms) == 1  # fallback to permission_classes


def test_get_permissions_fallback_when_no_map():
    """When permission_classes_map is not set, use permission_classes."""
    class ViewSet(CommonViewSet):
        permission_classes = [IsAuthenticated]

    viewset = ViewSet()
    viewset.action = 'list'
    perms = viewset.get_permissions()
    assert len(perms) == 1


def test_ok_defaults():
    response = CommonViewSet().ok()

    assert response.status_code == 200
    assert response.data == {'success': True}


def test_ok_with_payload():
    payload = {'message': 'done'}
    response = CommonViewSet().ok(payload)

    assert response.status_code == 200
    assert response.data == payload


def test_created_defaults():
    response = CommonViewSet().created()

    assert response.status_code == 201
    assert response.data == {'success': True}


def test_not_found_response():
    response = CommonViewSet().not_found()

    assert response.status_code == 404


def test_forbidden_default_and_custom_messages():
    viewset = CommonViewSet()

    default_response = viewset.forbidden()
    custom_response = viewset.forbidden({'detail': 'Nope'})

    assert default_response.status_code == 403
    assert default_response.data['detail'] == 'You do not have permission to perform this action.'
    assert custom_response.status_code == 403
    assert custom_response.data == {'detail': 'Nope'}


def test_bad_request_shapes_error_payload():
    response = CommonViewSet().bad_request(message='Invalid state', code='INVALID_STATE')

    assert response.status_code == 400
    assert response.data['errors']['message'] == ['Invalid state']
    assert response.data['errors']['code'] == 'INVALID_STATE'


def test_server_error_response():
    response = CommonViewSet().server_error(message='Database connection failed', code='DB_ERROR')

    assert response.status_code == 500
    assert response.data['errors']['message'] == ['Database connection failed']
    assert response.data['errors']['code'] == 'DB_ERROR'
    assert 'developerMessage' in response.data['errors']
