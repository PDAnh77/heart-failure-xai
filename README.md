# AI-Based Heart Failure Analytics System with Explainable AI (XAI)
## Overview
A comprehensive AI-powered platform for heart failure analysis and risk prediction. Leverage machine learning models with Explainable AI (XAI) to generate accurate, transparent insights from patient data. Explore end-to-end data workflows including preprocessing, exploratory data analysis (EDA), and feature selection to support data-driven clinical research and decision-making.

## Features
* **Heart Failure Risk Prediction**: Infer cardiovascular risk probability based on patient clinical features using trained ML models.

* **Explainable AI (XAI)**: Transparent, interpretable model predictions via SHAP (SHapley Additive exPlanations) and LIME (Local Interpretable Model-agnostic Explanations).

* **Dataset Management**: Upload CSV datasets, view summaries, run automated preprocessing, and manage training/batch prediction files.

* **Exploratory Data Analysis (EDA)**:
  - Correlation heatmaps and feature importance analysis
  - Target distribution analysis (pie charts and bar plots)
  - Chi-square scores for categorical features
  - ANOVA scores for numerical features

* **Automated Data Preprocessing**:
  - Duplicate removal
  - Missing value imputation
  - Label encoding for categorical variables
  - Feature scaling

* **Feature Selection**: Select optimal features using algorithms like Random Forest, XGBoost, and Decision Trees.

* **Model Training & Evaluation**: Train machine learning models (Logistic Regression, Random Forest, Decision Tree, XGBoost, LightGBM, SVC, KNN) with performance evaluation (Accuracy, Precision, Recall, F1-Score, Cross-Validation).

* **Patient & Prediction History**: Manage patient clinical profiles and track individual and batch prediction history over time.

## Model & XAI Description
* Features used for prediction:

| Feature | Type | Description |
| :--- | :--- | :--- |
| Age | Integer | Age of the patient (1–120 years) |
| Sex | String | Sex of the patient (`M`: Male, `F`: Female) |
| ChestPainType | String | Type of chest pain:<br>- `TA`: Typical Angina<br>- `ATA`: Atypical Angina<br>- `NAP`: Non-Anginal Pain<br>- `ASY`: Asymptomatic |
| RestingBP | Integer | Resting blood pressure (mm Hg) |
| Cholesterol | Integer | Serum cholesterol level (mm/dl) |
| FastingBS | Integer | Fasting blood sugar:<br>- `1`: Fasting blood sugar > 120 mg/dl<br>- `0`: Otherwise |
| RestingECG | String | Resting electrocardiogram results:<br>- `Normal`: Normal ECG<br>- `ST`: ST-T wave abnormality<br>- `LVH`: Left ventricular hypertrophy (Estes’ criteria) |
| MaxHR | Integer | Maximum heart rate achieved during exercise |
| ExerciseAngina | String | Exercise-induced angina:<br>- `Y`: Yes<br>- `N`: No |
| Oldpeak | Float | ST depression induced by exercise relative to rest |
| ST_Slope | String | Slope of the peak exercise ST segment:<br>- `Up`: Upsloping<br>- `Flat`: Flat<br>- `Down`: Downsloping |

* Output: Probability of heart failure along with corresponding XAI explanations

* XAI:
  - SHAP (SHapley Additive exPlanations)
  - LIME (Local Interpretable Model-agnostic Explanations)

## System Architecture
The following diagram illustrates the overall system architecture of the heart failure prediction application:

![System Architecture Diagram](docs/system_architecture.png)

## Repository Structure
The repository is organized as follows:
```.
.
├── .github/
│   └── workflows/          # CI/CD pipelines for backend & frontend deployment
│
├── api/                    # Backend API (FastAPI)
│   ├── core/               # Configuration, security, unified storage adapter
│   ├── db/                 # Database connection & auto-initialization
│   ├── models/             # SQLAlchemy ORM models
│   ├── routers/            # API route definitions & endpoints
│   ├── schemas/            # Pydantic request/response schemas
│   ├── services/           # Business logic (prediction, XAI, auth, dataset analysis)
│   ├── storage/            # Local file storage root (ignored by git)
│   ├── dependencies.py     # Shared FastAPI dependencies
│   ├── main.py             # FastAPI application entry point & static file mount
│   ├── Dockerfile          # Docker image build configuration
│   └── requirements.txt    # Backend dependencies
│
├── input/                  # Datasets used for training AI models
│
├── notebooks/              # Jupyter notebooks for data analysis & model training
│   └── models/             # Pretrained model files
│
├── web/                    # Frontend web application
│   ├── app/                # Application pages and layouts
│   ├── components/         # Reusable UI components
│   ├── context/            # Application context (auth, global state)
│   ├── lib/                # API clients and helper functions
│   ├── types/              # TypeScript type definitions
│   ├── public/             # Static assets
│   ├── README.md           # Frontend-specific setup instructions
│   ├── package.json        # Frontend dependencies
│   └── next.config.ts      # Web application configuration
│
├── requirements-dev.txt    # Development dependencies
└── README.md               # Project documentation
```

## Prerequisites
* **Python**: `3.13` (Recommend)
* **PostgreSQL**: `14+`
* **Node.js**: `20.9.0+`

## Installation & Setup

### 1. Database
Set up a PostgreSQL database locally or create a project on [Supabase](https://supabase.com).

### 2. Backend (API)
1. Navigate to `api/`:
   ```bash
   cd api/
   ```

2. Create and activate virtual environment:
   ```bash
   python -m venv venv
   # Windows:
   venv\Scripts\Activate.ps1
   # Linux/macOS:
   source venv/bin/activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Configure `.env` (see [Environment Variables](#environment-variables)).

5. Run the API:
   ```bash
   uvicorn main:app --reload
   ```

### 3. Frontend (Web)
1. Navigate to `web/`:
   ```bash
   cd web/
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Configure `.env.local` (see [Environment Variables](#environment-variables)).

4. Run the web application:
   ```bash
   npm run dev
   ```

---

## Environment Variables

### Backend (`api/.env`)
Create a `.env` file inside the `api/` directory:

```env
# Database: Local PostgreSQL or Supabase connection string
DATABASE_URL=postgresql://your_username:your_password@localhost:5432/your_database_name

# File Storage: 'local' (saves files in api/storage/) or 'supabase'
FILE_STORAGE_PROVIDER=local

# Supabase Credentials (required if FILE_STORAGE_PROVIDER=supabase)
SUPABASE_URL=
SUPABASE_SERVICE_ROLE_KEY=

# Authentication & URLs (examples for local development)
JWT_SECRET_KEY=your_secret_jwt_key
API_URL=http://localhost:8000
CLIENT_URL=http://localhost:3000

# Google OAuth (Optional)
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
REDIRECT_URI=http://localhost:8000/api/auth/google/callback
```

### Frontend (`web/.env.local`)
Create a `.env.local` file inside the `web/` directory:

```env
# URLs (examples for local development)
API_URL=http://localhost:8000
CLIENT_URL=http://localhost:3000
```

---

### CI/CD Pipeline
CI/CD workflows are located in the `.github/workflows/` directory:
* Building backend Docker images
* Running Trivy security scans
* Deploying backend and frontend applications to hosting platforms

## Usage
1. Access the web application via your browser (e.g., `http://localhost:3000` or your deployed URL)
2. Input patient clinical and health information via the web interface
3. Submit the data to receive heart failure risk predictions along with XAI explanations
4. View and manage prediction history through the user dashboard

## Disclaimer
This project is intended for educational and research purposes only. It should not be used as a substitute for professional medical advice, diagnosis, or treatment. Always seek the advice of your physician or other qualified health provider with any questions you may have regarding a medical condition.
