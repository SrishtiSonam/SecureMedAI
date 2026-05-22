# 🏥 CureShieldSynapse

> AI-powered healthcare platform for symptom-based disease prediction, smart doctor appointment booking, prescription management, and longitudinal health tracking.

CureShieldSynapse bridges the gap between intelligent diagnosis and timely medical care. Patients receive instant predictions based on symptoms and are connected with top-rated, relevant doctors. Doctors manage appointments and access patient history, while admins oversee the entire platform.

---

## ✨ Features

### Patient
- Symptom-based disease prediction using Random Forest
- Book appointments with matched doctors
- Rate and review doctors
- Secure real-time chat with doctors
- View and manage prescriptions and medications
- Track health history across visits on a longitudinal timeline

### Doctor
- Privacy-preserving diagnosis improvement using Federated Learning with **differential privacy** (TensorFlow Privacy)
- **Secure aggregation** — individual doctor model updates are never exposed during federation
- **Model versioning** — see which model version made each prediction
- View and manage appointments
- Issue and manage prescriptions
- Access patient information and longitudinal health history
- Receive and respond to ratings
- Secure real-time chat with patients

### Admin
- Manage users, doctors, and feedback
- View platform analytics
- Monitor system activity and model version deployments

---

## 🤖 AI & ML

| Model | Used By | Purpose |
|---|---|---|
| Random Forest | Patients | Client-side symptom-based disease prediction |
| Federated Learning + TF Privacy | Doctors | Privacy-preserving collaborative diagnosis improvement with differential privacy |

ML models are served as isolated microservices using **FastAPI + ONNX Runtime**, keeping inference decoupled from the main backend.

### Federated Learning Upgrades

**Differential Privacy (TensorFlow Privacy)**
Federated updates are clipped and noised using `tensorflow_privacy` before aggregation, providing formal DP guarantees. Each training round applies per-update L2 clipping and Gaussian noise addition so that no individual doctor's patient data can be inferred from model updates.

**Secure Aggregation**
A cryptographic secure aggregation protocol ensures the central server only ever sees the summed aggregate of encrypted updates — never any single doctor's raw gradient. Individual contributions are masked with secret-shared random vectors that cancel out in the sum.

**Model Versioning**
Every federated round produces a versioned model artifact (e.g. `v1.3.2`) stored with its training metadata. Prediction responses include `model_version` so doctors and patients always know which model version produced a given result. The admin dashboard surfaces version history and per-version performance metrics.

---

## 💊 Prescription & Medicine Management

Doctors issue structured digital prescriptions linked to appointments and diagnoses. Patients access their full prescription history and receive adherence reminders.

### Flow

```text
Doctor completes appointment
   ↓
Issues digital prescription (drug, dosage, frequency, duration, notes)
   ↓
Prescription stored → linked to Appointment + Patient
   ↓
Patient views active prescriptions in dashboard
   ↓
Refill requests sent to doctor via notification
   ↓
Adherence reminders delivered via in-app + email
```

### Data Model (Prisma)

```prisma
model Prescription {
  id            String   @id @default(cuid())
  appointmentId String
  patientId     String
  doctorId      String
  issuedAt      DateTime @default(now())
  medications   Medication[]
  notes         String?
  status        PrescriptionStatus @default(ACTIVE)
  appointment   Appointment @relation(fields: [appointmentId], references: [id])
  patient       User        @relation(fields: [patientId], references: [id])
  doctor        Doctor      @relation(fields: [doctorId], references: [id])
}

model Medication {
  id             String       @id @default(cuid())
  prescriptionId String
  name           String
  dosage         String
  frequency      String
  durationDays   Int
  instructions   String?
  prescription   Prescription @relation(fields: [prescriptionId], references: [id])
}

enum PrescriptionStatus {
  ACTIVE
  COMPLETED
  CANCELLED
  REFILL_REQUESTED
}
```

### API Endpoints (NestJS)

| Method | Endpoint | Role | Description |
|---|---|---|---|
| POST | `/prescriptions` | DOCTOR | Issue a new prescription |
| GET | `/prescriptions/patient/:id` | DOCTOR, PATIENT | Patient's prescription history |
| GET | `/prescriptions/:id` | DOCTOR, PATIENT | Single prescription detail |
| PATCH | `/prescriptions/:id/status` | DOCTOR | Update status (complete, cancel) |
| POST | `/prescriptions/:id/refill` | PATIENT | Request refill |

---

## 📅 Health Timeline & Longitudinal Tracking

Every patient has a unified health timeline aggregating appointments, diagnoses, prescriptions, and doctor ratings across their entire history on the platform.

### What is Tracked

| Event Type | Source | Data Captured |
|---|---|---|
| Appointment | Appointments module | Date, doctor, status, prediction used |
| Diagnosis | ML prediction + doctor confirmation | Disease, confidence score, model version |
| Prescription | Prescriptions module | Medications issued, dosages, duration |
| Vitals (optional) | Patient self-report | Weight, blood pressure, glucose, etc. |
| Rating | Ratings module | Doctor rated after visit |

### Timeline API

```text
GET /patients/:id/timeline
  → Returns chronological list of health events
  → Filterable by event type, date range, doctor

GET /patients/:id/timeline/summary
  → Aggregated stats: total visits, conditions seen, active medications
```

### Frontend Component

A dedicated `HealthTimeline` component renders events in reverse-chronological order with collapsible cards per event type. Color-coded badges distinguish diagnoses, prescriptions, and appointments. Doctors see the same timeline for any patient, enabling continuity of care across visits and providers.

---

## 🏗️ Tech Stack

### Backend
- **NestJS** — modular, scalable Node.js backend framework
- **Prisma ORM** — type-safe database access layer
- **MySQL** — relational database (hosted via PlanetScale or Supabase)

### Frontend
- **React.js** — component-based UI
- **Tailwind CSS** — utility-first styling
- **Recharts + Chart.js** — analytics and data visualization

### Authentication
- **Auth0** — secure, role-based authentication for Patients, Doctors, and Admins

### Real-Time
- **Socket.io** — bidirectional real-time patient-doctor chat

### ML Serving
- **FastAPI microservice** — dedicated ML inference server
- **ONNX Runtime** — optimized model serving for Random Forest and Federated Learning models
- **TensorFlow Privacy** — differential privacy for federated updates

---

## 📂 Project Structure

```text
CureShieldSynapse/
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── Auth/
│   │   │   ├── Dashboard/
│   │   │   ├── Prediction/
│   │   │   ├── Appointments/
│   │   │   ├── Chat/
│   │   │   ├── Ratings/
│   │   │   ├── Prescriptions/       ← NEW: issue, view, refill
│   │   │   └── HealthTimeline/      ← NEW: longitudinal event feed
│   │   ├── pages/
│   │   │   ├── patient/
│   │   │   ├── doctor/
│   │   │   └── admin/
│   │   ├── hooks/
│   │   ├── store/
│   │   └── utils/
│   ├── public/
│   ├── tailwind.config.js
│   └── package.json
│
├── backend/
│   ├── src/
│   │   ├── auth/                  ← Auth0 integration + guards
│   │   ├── users/                 ← Patient & Doctor modules
│   │   ├── appointments/          ← Booking logic
│   │   ├── chat/                  ← Socket.io gateway
│   │   ├── ratings/               ← Doctor rating system
│   │   ├── analytics/             ← Admin analytics
│   │   ├── prescriptions/         ← NEW: CRUD + refill requests
│   │   ├── timeline/              ← NEW: longitudinal health events
│   │   └── main.ts
│   ├── prisma/
│   │   └── schema.prisma          ← DB models
│   └── package.json
│
├── ml_service/
│   ├── main.py                    ← FastAPI ML server
│   ├── models/
│   │   ├── random_forest.onnx     ← Patient prediction model
│   │   └── federated_model.onnx   ← Doctor federated model
│   ├── versioning/
│   │   ├── registry.py            ← NEW: model version store
│   │   └── metadata.json          ← NEW: version → training metadata
│   ├── routers/
│   │   ├── predict.py             ← Returns model_version in response
│   │   └── federated.py           ← DP + secure aggregation
│   ├── federated/
│   │   ├── dp_trainer.py          ← NEW: TF Privacy DP-SGD wrapper
│   │   └── secure_aggregation.py  ← NEW: masked gradient aggregation
│   └── requirements.txt
│
├── .env.example
├── docker-compose.yml
└── README.md
```

---

## 🗄️ Database Models (Prisma)

```prisma
model User {
  id            String   @id @default(cuid())
  email         String   @unique
  role          Role
  name          String
  createdAt     DateTime @default(now())
  appointments  Appointment[]
  ratings       Rating[]
  prescriptions Prescription[]
  healthEvents  HealthEvent[]
}

model Doctor {
  id             String   @id @default(cuid())
  userId         String   @unique
  specialization String
  experience     Int
  languages      String[]
  availability   Boolean  @default(true)
  rating         Float    @default(0)
  appointments   Appointment[]
  ratings        Rating[]
  prescriptions  Prescription[]
}

model Appointment {
  id            String            @id @default(cuid())
  patientId     String
  doctorId      String
  scheduledAt   DateTime
  status        AppointmentStatus @default(PENDING)
  prediction    String?
  modelVersion  String?           // NEW: which model version was used
  prescriptions Prescription[]
  patient       User              @relation(fields: [patientId], references: [id])
  doctor        Doctor            @relation(fields: [doctorId], references: [id])
}

model Rating {
  id        String  @id @default(cuid())
  score     Int
  comment   String?
  patientId String
  doctorId  String
  patient   User    @relation(fields: [patientId], references: [id])
  doctor    Doctor  @relation(fields: [doctorId], references: [id])
}

// NEW
model Prescription {
  id            String             @id @default(cuid())
  appointmentId String
  patientId     String
  doctorId      String
  issuedAt      DateTime           @default(now())
  notes         String?
  status        PrescriptionStatus @default(ACTIVE)
  medications   Medication[]
  appointment   Appointment        @relation(fields: [appointmentId], references: [id])
  patient       User               @relation(fields: [patientId], references: [id])
  doctor        Doctor             @relation(fields: [doctorId], references: [id])
}

// NEW
model Medication {
  id             String       @id @default(cuid())
  prescriptionId String
  name           String
  dosage         String
  frequency      String
  durationDays   Int
  instructions   String?
  prescription   Prescription @relation(fields: [prescriptionId], references: [id])
}

// NEW
model HealthEvent {
  id        String          @id @default(cuid())
  patientId String
  eventType HealthEventType
  eventDate DateTime
  metadata  Json            // flexible: diagnosis, prescription ref, vitals, etc.
  patient   User            @relation(fields: [patientId], references: [id])
}

enum Role {
  PATIENT
  DOCTOR
  ADMIN
}

enum AppointmentStatus {
  PENDING
  CONFIRMED
  CANCELLED
  COMPLETED
}

// NEW
enum PrescriptionStatus {
  ACTIVE
  COMPLETED
  CANCELLED
  REFILL_REQUESTED
}

// NEW
enum HealthEventType {
  APPOINTMENT
  DIAGNOSIS
  PRESCRIPTION
  VITAL
  RATING
}
```

---

## 🔐 Authentication Flow (Auth0)

```text
User visits platform
   ↓
Auth0 Universal Login
   ↓
Role assigned: PATIENT / DOCTOR / ADMIN
   ↓
Auth0 issues access token
   ↓
NestJS guards validate token on every request
   ↓
Role-based route access enforced
```

---

## 💬 Real-Time Chat Flow (Socket.io)

```text
Patient opens chat with Doctor
   ↓
Socket.io connection established
   ↓
Messages emitted to private room: room:{patientId}:{doctorId}
   ↓
Both parties receive messages in real time
   ↓
Messages persisted to MySQL via Prisma
```

---

## 🤖 ML Serving Flow (FastAPI + ONNX)

```text
Patient enters symptoms
   ↓
React frontend → POST /ml/predict
   ↓
FastAPI ML microservice
   ↓
ONNX Runtime loads Random Forest model (active version from registry)
   ↓
Inference → predicted disease + confidence score + model_version
   ↓
Result returned to frontend
   ↓
Smart doctor matching triggered based on prediction
```

---

## 🔒 Federated Learning Flow (with DP + Secure Aggregation)

```text
Federated round initiated by server
   ↓
Selected doctors receive global model weights
   ↓
Local training on private patient data (never leaves device/hospital)
   ↓
TF Privacy DP-SGD: per-update L2 gradient clipping + Gaussian noise
   ↓
Masked update generated (secret-shared random vector added)
   ↓
Encrypted masked updates sent to server
   ↓
Server aggregates sum → random masks cancel → clean aggregate only
   ↓
Global model updated → versioned and stored in registry
   ↓
New model version deployed; prior versions archived
```

---

## 🧠 Smart Doctor Matching

Doctors are ranked by:
- Specialization match to predicted disease
- Rating score
- Availability
- Experience (years)
- Languages spoken

---

## ⚙️ Installation & Setup

### Prerequisites
- Node.js 18+
- Python 3.10+
- MySQL
- Auth0 account

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Backend

```bash
cd backend
npm install
npx prisma migrate dev
npm run start:dev
```

### ML Service

```bash
cd ml_service
python -m venv env
source env/bin/activate        # Windows: .\env\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8001
```

---

## 🔑 Environment Variables

```env
# Backend
DATABASE_URL=mysql://user:password@localhost:3306/cureshield
AUTH0_DOMAIN=your-domain.auth0.com
AUTH0_AUDIENCE=your-api-audience
AUTH0_CLIENT_ID=
AUTH0_CLIENT_SECRET=

# Frontend
REACT_APP_AUTH0_DOMAIN=your-domain.auth0.com
REACT_APP_AUTH0_CLIENT_ID=
REACT_APP_ML_SERVICE_URL=http://localhost:8001
REACT_APP_BACKEND_URL=http://localhost:3000

# ML Service
MODEL_PATH=./models
MODEL_REGISTRY_PATH=./versioning/metadata.json
DP_NOISE_MULTIPLIER=1.1
DP_MAX_GRAD_NORM=1.0
```

---

## 🚀 Deployment

```bash
# All services
docker-compose up --build
```

---

## 🛡️ License

MIT License
