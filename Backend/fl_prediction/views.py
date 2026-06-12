from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser

from . import ml_model


class FLPredictView(APIView):
    """
    POST /api/fl/predict/

    Upload a medical report image. The image is OCR-processed, the extracted
    symptom text is classified by the BERT federated model, and a SHAP
    explanation HTML string is returned alongside the prediction.

    Request  : multipart/form-data  { image: <file> }
    Response : {
        predicted_disease : str,
        extracted_text    : str,
        shap_html         : str | null
    }
    """

    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser]

    def post(self, request, format=None):
        if 'image' not in request.FILES:
            return Response(
                {'error': 'No image file provided. Send an image under the "image" field.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        result = ml_model.predict_from_image(request.FILES['image'])

        if 'error' in result:
            return Response(result, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

        return Response(result, status=status.HTTP_200_OK)
