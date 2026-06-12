from django.urls import path
from .views import FLPredictView

urlpatterns = [
    path('fl/predict/', FLPredictView.as_view(), name='fl-predict'),
]
