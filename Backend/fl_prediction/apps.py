from django.apps import AppConfig


class FlPredictionConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'fl_prediction'

    def ready(self):
        from . import ml_model
        ml_model.load_models()
