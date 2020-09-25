from rest_framework.renderers import JSONRenderer
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import RequestSerializer


class BatchRequestsView(APIView):
    permission_classes = ()
    authentication_classes = ()
    renderer_classes = (JSONRenderer,)

    def post(self, request: Request):
        serializer = RequestSerializer(data=request.data, many=True)
        serializer.is_valid(raise_exception=True)
        return Response({})
