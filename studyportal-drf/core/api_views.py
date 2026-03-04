from rest_framework import status
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from utils.permissions import permissions_for_action


class CommonViewSet(GenericViewSet):
    """
    Common view set for all view sets
    - create response
    - optional action-based permissions when permission_classes_map is set
    """

    def get_permissions(self):
        """
        Use action-based permissions when permission_classes_map is defined,
        otherwise fall back to DRF default (instantiate permission_classes).
        """
        permission_classes_map = getattr(self, 'permission_classes_map', None)
        if permission_classes_map is not None:
            return permissions_for_action(
                action=self.action,
                permission_classes_map=permission_classes_map,
                default_permissions=self.permission_classes,
            )
        return [permission() for permission in self.permission_classes]

    def ok(self, data: dict | None = None) -> Response:
        """
        Default response ok. Status code is 200
        """
        if not data:
            data = {'success': True}

        return Response(data=data, status=status.HTTP_200_OK)

    def created(self, data: dict | None = None) -> Response:
        """
        Default response created. Status code is 201
        """
        if not data:
            data = {'success': True}

        return Response(data=data, status=status.HTTP_201_CREATED)

    def not_found(self) -> Response:
        """
        Default response not found. Status code is 404
        """
        return Response(status=status.HTTP_404_NOT_FOUND)

    def forbidden(self, data: dict | None = None) -> Response:
        """
        Default response forbidden. Status code is 403
        """
        if not data:
            data = {
                'detail': 'You do not have permission to perform this action.',
            }

        return Response(data=data, status=status.HTTP_403_FORBIDDEN)

    def bad_request(self, message=None, code=None):
        """
        Return bad request with message content & code
        """
        # Build up the error content.
        response_data = {
            'errors': {
                'developerMessage': 'API is not working properly.',
                'message': [message],
                'code': code,
            },
        }

        return Response(data=response_data, status=status.HTTP_400_BAD_REQUEST)

    def server_error(self, message=None, code=None):
        """
        Return internal server error with message content & code
        """
        # Build up the error content.
        response_data = {
            'errors': {
                'developerMessage': 'API is not working properly.',
                'message': [message],
                'code': code,
            },
        }

        return Response(data=response_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
