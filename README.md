# CureShieldSynapse

> AI-powered healthcare platform combining symptom-based disease prediction, federated learning, smart doctor matching, appointment management, and longitudinal health tracking — all in a privacy-first architecture.

CureShieldSynapse bridges intelligent diagnosis and timely medical care. Patients get instant disease predictions from their symptoms and are connected with top-rated relevant doctors. Doctors manage appointments, access patient history, and contribute to a privacy-preserving federated learning system. Admins oversee platform operations and user approvals.

---

## Table of Contents

- [Features](#features)
- [Tech Stack](#tech-stack)
- [Architecture](#architecture)
- [ML Systems](#ml-systems)
- [Project Structure](#project-structure)
- [Installation & Setup](#installation--setup)
- [Environment Variables](#environment-variables)
- [API Overview](#api-overview)
- [Contributing](#contributing)
- [License](#license)

---

## Features

### Patient
- Symptom-based disease prediction using a trained Random Forest model
- Smart doctor matching by specialization, rating, experience, and language
- Appointment booking and management
- View and track prescriptions and medications
- Longitudinal health timeline across all visits
- Rate and review doctors
- Real-time chat with doctors

### Doctor
- Appointment management with full patient history access
- Issue and manage digital prescriptions
- Participate in federated learning to improve the global DistilBERT diagnosis model — patient data never leaves the local environment
- Privacy-preserving training with Opacus DP-SGD (per-sample gradient clipping + Gaussian noise, ε ≤ 8.0 at δ = 1e-5)
- Receive and respond to patient ratings
- Real-time chat with patients

### Admin
- User approval workflow for doctors and patients
- User management (view, suspend, manage roles)
- Platform-wide analytics and monitoring

---

## Tech Stack

| Layer | Technology |
|---|---|
| **Frontend** | React 19, Tailwind CSS 3, React Router v7, TanStack Query 5 |
| **State & Forms** | React Hook Form 7, Axios 1.8 |
| **Auth** | Firebase Authentication (JWT-based, role-aware) |
| **Backend** | Django 5.2, Django REST Framework |
| **Database** | PostgreSQL (via Django ORM) |
| **Backend Auth** | djangorestframework-simplejwt + Firebase token verification |
| **ML — Prediction** | scikit-learn 1.6 (Random Forest), pandas, numpy |
| **ML — Federated** | PyTorch 2.2, HuggingFace Transformers (DistilBERT), SHAP, Opacus 1.4 |
| **OCR** | Tesseract OCR + OpenCV + Pillow |
| **AI Insights** | Google Generative AI (Gemini) |
| **Class Balancing** | imbalanced-learn (SMOTE) |
| **Icons** | Lucide React |
| **Date Utils** | date-fns 4 |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Browser / Client                     │
│              React 19  ·  Tailwind CSS  ·  Firebase Auth    │
└───────────────────────────┬─────────────────────────────────┘
                            │ REST (JWT)
                            ▼
                  ┌───────────────────────┐
                  │   Django REST API     │
                  │   + PostgreSQL        │
                  │                       │
                  │  ┌─────────────────┐  │
                  │  │ prediction app  │  │  ← Random Forest (RF)
                  │  │ (scikit-learn)  │  │
                  │  └─────────────────┘  │
                  │  ┌─────────────────┐  │
                  │  │ fl_prediction   │  │  ← DistilBERT + SHAP + OCR
                  │  │ app (PyTorch)   │  │     DP-SGD · FedProx · Top-k
                  │  └─────────────────┘  │
                  └───────────────────────┘
```

**Authentication flow:**
1. User registers / logs in via Firebase
2. Firebase issues a JWT
3. React stores the token and attaches it to every API request via Axios interceptors
4. Django verifies the Firebase token and maps it to a local User (PATIENT / DOCTOR / ADMIN)
5. Role-based route guards in both React (`ProtectedRoute`) and Django (DRF permissions)

---

## ML Systems

### 1. Random Forest — Symptom Prediction

Located in `ML Model/`. Serves as the primary, always-available prediction engine.

- **Input:** Binary-encoded symptom vector (132 unique symptoms)
- **Output:** Top-3 disease predictions with confidence scores
- **Training data:** `disease_symptoms_binary.csv` augmented with a noisy variant for robustness
- **Class balancing:** SMOTE (imbalanced-learn) to address label skew
- **Artifacts:** `RFsymptomsmodel.pkl` loaded by the Django `prediction` app
- **Minimum symptoms:** 5 symptoms required for a valid prediction

The model is embedded directly in the Django backend (`prediction/ml_model.py`) and called synchronously on prediction requests.

### 2. Federated Learning — DistilBERT Diagnosis (Privacy-Preserving)

Located in `FL Model/`. Training notebook produces artifacts consumed by the `fl_prediction` Django app — no separate service needed.

**Model:** `distilbert-base-uncased` fine-tuned for 58-class disease classification  
— 40% smaller and 60% faster than BERT with ~97% accuracy retention  
**Serving:** `fl_prediction` Django app — loads `global_model1.pt` + tokenizer + `label_encoder.pkl` once at startup via `AppConfig.ready()`  
**Explainability:** SHAP text-plot HTML returned inline in the JSON response  
**OCR Pipeline:** Tesseract extracts symptom text from uploaded medical report images → DistilBERT inference

#### Evaluation metrics (post-training)

Every client and the global model now report:

| Metric | What it measures |
|---|---|
| Accuracy | Overall correct predictions |
| Weighted F1 | F1 averaged by class frequency — robust for imbalanced 58-class data |
| Macro F1 | F1 averaged equally across all classes — flags rare-disease failures |
| Per-class precision / recall | Full `classification_report` per client and global model |

#### Privacy — Opacus DP-SGD (Phase 2)

Plain HuggingFace Trainer is replaced by a custom **Opacus DP-SGD loop** per client:

1. `ModuleValidator.fix(model)` — swaps multi-head attention for a DP-safe implementation
2. `PrivacyEngine.make_private_with_epsilon()` — wraps optimizer + DataLoader to enforce **per-sample gradient clipping** (L2 norm ≤ 1.0) and **Gaussian noise injection**
3. `privacy_engine.get_epsilon(delta=1e-5)` — cumulative ε tracked and printed every 5 epochs

Target: `ε = 8.0` at `δ = 1e-5` (configurable). `USE_DP = False` falls back to plain Trainer.

#### Non-IID Data — Dirichlet Partitioning (Phase 3)

Real hospitals have heavy label skew. `dirichlet_partition(alpha)` re-distributes the combined training data using a Dirichlet(α) draw per disease class:

| α | Effect |
|---|---|
| 0.1 | High skew — each client owns mostly 1–2 diseases |
| **0.5** | **Moderate skew (default)** |
| 100 | Near-IID |

`USE_DIRICHLET = False` restores the original dataset splits.

#### FedProx Aggregation (Phase 3)

`FedProxTrainer` subclasses HuggingFace `Trainer` and injects a proximal penalty into every batch loss:

```
loss = CE_loss + (μ/2) · ‖w_local − w_global‖²
```

This anchors local updates to the global model, preventing client drift under heterogeneous data. `FEDPROX_MU = 0` degrades to plain FedAvg. Default: `μ = 0.01`.

#### Top-k Gradient Compression (Phase 3)

DistilBERT has 67M parameters. `federated_averaging` now compresses per-client **deltas** (not raw weights) before aggregation:

```
delta_i           = local_params_i − global_params
compressed_delta_i = top_k(delta_i, sparsity=0.99)   ← keep top 1%
new_global        = global + Σ weight_i · compressed_delta_i
```

At `TOP_K_SPARSITY = 0.99` this transmits only **1% of parameters per client** — a ~100× reduction in communication — with minimal accuracy impact (per Lin et al. 2018). The aggregation cell prints the actual transmission ratio.

#### Federated round flow (full pipeline)

```
Configure: USE_DIRICHLET=True, USE_DP=True, USE_FEDPROX=True
  ↓
Dirichlet(α=0.5) re-partitions combined data → realistic label skew per client
  ↓
Each client: Opacus DP-SGD training
    per-sample gradient clipping (‖g‖₂ ≤ 1.0)
    + Gaussian noise (σ=1.1)
    + FedProx proximal term (μ=0.01)
  ↓
Privacy budget checked: ε ≤ 8.0 at δ=1e-5
  ↓
Top-k compression: only top 1% of delta uploaded
  ↓
Server: weighted FedAvg on compressed deltas → new global model
  ↓
Evaluate: accuracy + weighted F1 + macro F1 + per-class report
  ↓
Save: global_model1.pt, tokenizer/, label_encoder.pkl
```

---

## Project Structure

```
CureShieldSynapse/
│
├── Frontend/                        # React 19 web application
│   ├── public/
│   └── src/
│       ├── components/
│       │   ├── auth/                # LoginForm, RegisterForm, RoleSelector
│       │   ├── patient/             # PatientDashboard, BookAppointment,
│       │   │                        # MyAppointments, PatientProfile
│       │   ├── doctor/              # DoctorDashboard, AppointmentsList,
│       │   │                        # DoctorProfile, PatientHistory
│       │   ├── admin/               # AdminDashboard, UserManagement,
│       │   │                        # DoctorApproval, PatientApproval
│       │   └── common/              # ProtectedRoute, Navbar, Sidebar,
│       │                            # LoadingSpinner
│       ├── pages/                   # home, login, signup, prediction,
│       │                            # doctors, appointment, medical-history,
│       │                            # appoint-history
│       ├── services/
│       │   ├── api.js               # Axios instance with JWT interceptors
│       │   ├── doctorService.js
│       │   └── patientService.js
│       ├── utils/Router.js          # React Router with protected routes
│       ├── firebase.js              # Firebase auth config
│       ├── App.js
│       └── index.js
│
├── Backend/                         # Django 5.2 REST API
│   ├── authentication/              # User model, JWT login/signup, roles
│   ├── prediction/                  # RF model loading + inference API
│   ├── fl_prediction/               # DistilBERT federated model (replaces Flask)
│   │   ├── apps.py                  #   loads DistilBERT once at startup
│   │   ├── ml_model.py              #   OCR → DistilBERT inference → SHAP
│   │   ├── views.py                 #   POST /api/fl/predict/
│   │   └── urls.py
│   ├── doctor/                      # Doctor profiles, specialization filter
│   ├── patient/                     # Patient profiles, health records
│   ├── patient_dashboard/           # Vitals tracking (heart rate, BP, glucose)
│   ├── admin/                       # Approval workflows, user management
│   ├── account/                     # Account management
│   ├── management/commands/         # Seed scripts: populate_diseases,
│   │                                # populate_doctors, create_test_users
│   ├── firebase_config.py           # Firebase Admin SDK init
│   ├── firebase_auth.py             # Firebase token verification
│   └── backend/
│       ├── settings.py
│       └── urls.py
│
├── ML Model/                        # Standalone Random Forest training
│   ├── RFsymptomsmodel.pkl          # Trained model artifact
│   ├── ModelRun.py                  # Training + evaluation script
│   ├── model_tuning.py              # Hyperparameter search
│   ├── symptoms.py                  # Feature engineering
│   ├── dataset.csv
│   ├── disease_symptoms_binary.csv
│   ├── disease_symptoms_binary_noisy.csv
│   └── unique_symptoms_list.csv     # Full feature list (132 symptoms)
│
├── FL Model/                        # Federated Learning — training & artifacts
│   ├── flask/                       # Model artifacts (consumed by Django)
│   │   ├── global_model1.pt         #   Global DistilBERT weights (retrain to update)
│   │   ├── label_encoder.pkl        #   58-class disease label mapping
│   │   └── tokenizer/               #   DistilBERT tokenizer artifacts
│   ├── training/
│   │   └── training_fed_exp_bert.ipynb   # FL training: DistilBERT + DP-SGD +
│   │                                     # FedProx + Dirichlet + Top-k compression
│   ├── testing/
│   │   └── bert_test.ipynb
│   ├── image recognition/           # OCR training datasets
│   ├── FL.md                        # Detailed FL documentation
│   └── requirements.txt
│
├── CONTRIBUTING.md
├── CODE_OF_CONDUCT.md
├── SECURITY.md
├── LICENSE
└── requirements.txt                 # Root Python dependencies
```

---

## Installation & Setup

### Prerequisites

- Node.js 18+
- Python 3.10+
- PostgreSQL
- Firebase project (for authentication)
- Tesseract OCR (for FL model OCR pipeline)

---

### Frontend

```bash
cd Frontend
npm install
npm start
```

The dev server starts at `http://localhost:3000`.

---

### Backend

```bash
cd Backend

# Create and activate virtual environment
python -m venv venv
# Windows:
.\venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

pip install -r requirements.txt

# Ensure Tesseract OCR is installed (needed for the FL prediction endpoint)
# Windows: https://github.com/UB-Mannheim/tesseract/wiki
# macOS:   brew install tesseract
# Ubuntu:  sudo apt install tesseract-ocr

# Configure environment (see Environment Variables section)
cp backend/.env.example backend/.env

# Apply migrations
python manage.py migrate

# (Optional) Seed the database
python manage.py populate_diseases
python manage.py populate_doctors
python manage.py create_test_users

# Start the server
python manage.py runserver
```

The API runs at `http://localhost:8000`.

---

---

### FL Model — Retraining (optional)

The trained artifacts in `FL Model/flask/` are ready to use. To retrain on Kaggle or locally:

```bash
# Install FL training dependencies
pip install torch transformers datasets opacus>=1.4.0 shap imbalanced-learn

# Open the notebook (Kaggle GPU recommended)
# FL Model/training/training_fed_exp_bert.ipynb
```

**Training flags** at the top of the notebook — set before running:

| Flag | Default | Effect |
|---|---|---|
| `USE_DIRICHLET` | `True` | Non-IID Dirichlet(α) data partitioning |
| `DIRICHLET_ALPHA` | `0.5` | Skew level (lower = more heterogeneous) |
| `USE_DP` | `True` | Opacus DP-SGD (enforces ε ≤ 8.0 guarantee) |
| `TARGET_EPSILON` | `8.0` | DP privacy budget per client |
| `USE_FEDPROX` | `True` | FedProx proximal anchoring (μ = 0.01) |
| `TOP_K_SPARSITY` | `0.99` | Gradient compression — top 1% of delta |

After training, copy the three output files into `FL Model/flask/`:
```
global_model1.pt   →  FL Model/flask/global_model1.pt
tokenizer/         →  FL Model/flask/tokenizer/
label_encoder.pkl  →  FL Model/flask/label_encoder.pkl
```

---

### Random Forest Model (training only)

The trained `RFsymptomsmodel.pkl` is already used by the Django backend. To retrain:

```bash
cd "ML Model"
pip install scikit-learn pandas numpy imbalanced-learn
python ModelRun.py
```

---

## Environment Variables

### Backend (`Backend/backend/.env`)

```env
SECRET_KEY=your-django-secret-key
DEBUG=True

# PostgreSQL
DB_NAME=cureshield
DB_USER=your_db_user
DB_PASSWORD=your_db_password
DB_HOST=localhost
DB_PORT=5432

# Firebase Admin SDK
FIREBASE_CREDENTIALS_PATH=path/to/serviceAccountKey.json

# Google Generative AI (Gemini)
GEMINI_API_KEY=your-gemini-api-key

# CORS
CORS_ALLOWED_ORIGINS=http://localhost:3000

# Federated Learning
# Absolute path to FL Model/flask/ (default: auto-detected relative to Backend/)
FL_MODEL_DIR=
# Windows Tesseract binary path; leave blank if tesseract is on PATH
TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe
```

### Frontend (`Frontend/.env`)

```env
REACT_APP_FIREBASE_API_KEY=
REACT_APP_FIREBASE_AUTH_DOMAIN=
REACT_APP_FIREBASE_PROJECT_ID=
REACT_APP_FIREBASE_STORAGE_BUCKET=
REACT_APP_FIREBASE_MESSAGING_SENDER_ID=
REACT_APP_FIREBASE_APP_ID=

REACT_APP_BACKEND_URL=http://localhost:8000
```

---

## API Overview

All endpoints require a Firebase JWT in the `Authorization: Bearer <token>` header unless noted.

### Authentication

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/auth/register/` | Register new user (patient or doctor) |
| POST | `/api/auth/login/` | Login — returns JWT pair |
| POST | `/api/auth/token/refresh/` | Refresh access token |

### Prediction

| Method | Endpoint | Role | Description |
|---|---|---|---|
| POST | `/api/prediction/predict/` | PATIENT | Symptom list → top-3 disease predictions |
| GET | `/api/prediction/history/` | PATIENT | Past predictions for current user |

### Doctors

| Method | Endpoint | Role | Description |
|---|---|---|---|
| GET | `/api/doctors/` | Any | List doctors, filter by specialization |
| GET | `/api/doctors/:id/` | Any | Doctor profile detail |

### Federated Learning Prediction

| Method | Endpoint | Role | Description |
|---|---|---|---|
| POST | `/api/fl/predict/` | PATIENT, DOCTOR | Upload medical report image → OCR → BERT disease prediction + SHAP HTML |

Request: `multipart/form-data` with field `image` (JPEG/PNG medical report).  
Response: `{ predicted_disease, extracted_text, shap_html }` — `shap_html` is an inline HTML string for the explanation plot.

### Appointments

| Method | Endpoint | Role | Description |
|---|---|---|---|
| POST | `/api/appointments/` | PATIENT | Book appointment |
| GET | `/api/appointments/` | PATIENT, DOCTOR | List appointments (scoped to user) |
| PATCH | `/api/appointments/:id/` | DOCTOR | Update status |

### Patient Dashboard

| Method | Endpoint | Role | Description |
|---|---|---|---|
| GET | `/api/patient/profile/` | PATIENT | Patient profile |
| POST | `/api/patient/vitals/` | PATIENT | Log vitals (BP, weight, glucose, heart rate) |
| GET | `/api/patient/history/` | PATIENT, DOCTOR | Medical history timeline |

### Admin

| Method | Endpoint | Role | Description |
|---|---|---|---|
| GET | `/api/admin/users/` | ADMIN | All users |
| POST | `/api/admin/approve/doctor/:id/` | ADMIN | Approve doctor account |
| POST | `/api/admin/approve/patient/:id/` | ADMIN | Approve patient account |

---

## Smart Doctor Matching

When a prediction is returned, the platform ranks available doctors by:

1. **Specialization** — matched to the predicted disease category
2. **Rating** — higher-rated doctors rank above equal-specialization peers
3. **Availability** — only available doctors are shown
4. **Experience** — used as a secondary tiebreaker
5. **Languages** — surfaces language-match as a filter option

The Disease model in the backend maps each disease to one of 12 medical specializations, which drives the matching query.

---

## Health Timeline & Longitudinal Tracking

Each patient has a unified timeline aggregating:

| Event | Data Captured |
|---|---|
| Appointment | Date, doctor, status, prediction used |
| Diagnosis | Disease, confidence score |
| Prescription | Medications, dosages, duration, status |
| Vitals | Weight, blood pressure, glucose, heart rate |
| Rating | Doctor rated after visit |

The `HealthTimeline` React component renders events in reverse-chronological order with collapsible per-event cards. Doctors have read access to the same timeline for their patients.

---

## Contributing

We welcome contributions of all sizes. Please read [CONTRIBUTING.md](CONTRIBUTING.md) before opening a pull request. CureShieldSynapse participates in **GSSoC '25** — contributions are scored at three levels (Level 1: documentation fixes, Level 2: feature additions, Level 3: ML/architectural improvements).

Key guidelines:
- Open an issue before starting non-trivial work
- Follow the existing code style (ESLint for frontend, PEP 8 for Python)
- All ML changes must include evaluation metrics before and after
- Do not commit real patient data or API credentials

For security vulnerabilities, see [SECURITY.md](SECURITY.md).

---

## License

MIT License — Copyright 2025 SrishtiSonam. See [LICENSE](LICENSE) for full terms.
