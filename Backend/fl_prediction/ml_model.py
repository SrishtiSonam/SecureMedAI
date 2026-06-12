import os
import re
import torch
import shap
import joblib
import numpy as np
from PIL import Image
import pytesseract
from transformers import DistilBertForSequenceClassification, DistilBertTokenizerFast
from django.conf import settings

_model = None
_tokenizer = None
_label_encoder = None
_device = None


def load_models():
    global _model, _tokenizer, _label_encoder, _device

    fl_dir = settings.FL_MODEL_DIR

    tesseract_cmd = getattr(settings, 'TESSERACT_CMD', None)
    if tesseract_cmd:
        pytesseract.pytesseract.tesseract_cmd = tesseract_cmd

    _device = torch.device('cpu')

    _tokenizer = DistilBertTokenizerFast.from_pretrained(
        os.path.join(fl_dir, 'tokenizer')
    )
    _label_encoder = joblib.load(os.path.join(fl_dir, 'label_encoder.pkl'))

    num_labels = len(_label_encoder.classes_)
    weights_path = os.path.join(fl_dir, 'global_model1.pt')

    _model = DistilBertForSequenceClassification.from_pretrained(
        'distilbert-base-uncased', num_labels=num_labels
    )
    if os.path.exists(weights_path):
        _model.load_state_dict(torch.load(weights_path, map_location=_device))

    _model.to(_device)
    _model.eval()


def _preprocess_text(text):
    if not isinstance(text, str) or not text.strip():
        return None
    text = re.sub(r'(?i)patient report|patient name:.*|date:.*|hospital name:.*', '', text)
    text = re.sub(r'\b\w{1,2}\b', '', text)
    match = re.search(r'(?i)symptoms:\s*(.*)', text, re.DOTALL)
    text = match.group(1) if match else text
    text = re.sub(r'[^\w\s]', '', text)
    text = re.sub(r'Hospital Name:.*', '', text)
    text = re.sub(r'\n+', '\n', text).strip()
    text = text.replace('|', 'I')
    text = re.sub(r'[^\x00-\x7F]+', '', text)
    return text.strip() or None


def _predict_label(text):
    tokenized = _tokenizer(
        text,
        return_tensors='pt',
        padding=True,
        truncation=True,
        max_length=256,
    ).to(_device)

    with torch.no_grad():
        logits = _model(**tokenized).logits

    idx = torch.argmax(logits, dim=1).cpu().numpy()[0]
    return _label_encoder.inverse_transform([idx])[0]


def _generate_shap_html(text):
    id2label = {i: label for i, label in enumerate(_label_encoder.classes_)}

    def _wrapper(input_texts):
        if isinstance(input_texts, np.ndarray):
            input_texts = input_texts.tolist()
        elif isinstance(input_texts, str):
            input_texts = [input_texts]
        tokenized = _tokenizer(
            input_texts,
            return_tensors='pt',
            padding=True,
            truncation=True,
            max_length=256,
        ).to(_device)
        with torch.no_grad():
            logits = _model(**tokenized).logits
        return logits.cpu().numpy()

    masker = shap.maskers.Text(_tokenizer)
    explainer = shap.Explainer(_wrapper, masker)
    shap_values = explainer([text])
    shap_values.output_names = [id2label[i] for i in range(len(id2label))]

    # shap.plots.text returns an HTML string when display=False
    try:
        return shap.plots.text(shap_values, display=False)
    except TypeError:
        # Older SHAP versions use shap.text_plot
        return shap.text_plot(shap_values, display=False)


def predict_from_image(image_file):
    """
    Accepts a file-like object (Django InMemoryUploadedFile or similar).
    Returns a dict with keys: predicted_disease, extracted_text, shap_html.
    On failure returns a dict with key: error.
    """
    if _model is None:
        return {'error': 'FL model is not loaded.'}

    try:
        img = Image.open(image_file)
        raw_text = pytesseract.image_to_string(img)
    except Exception as e:
        return {'error': f'Failed to read image: {str(e)}'}

    cleaned_text = _preprocess_text(raw_text)
    if not cleaned_text:
        return {'error': 'No valid text could be extracted from the image.'}

    try:
        disease = _predict_label(cleaned_text)
    except Exception as e:
        return {'error': f'Prediction failed: {str(e)}'}

    shap_html = None
    try:
        shap_html = _generate_shap_html(cleaned_text)
    except Exception:
        pass  # SHAP is best-effort; prediction is still returned

    return {
        'predicted_disease': disease,
        'extracted_text': cleaned_text,
        'shap_html': shap_html,
    }
