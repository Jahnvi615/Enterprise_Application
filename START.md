# BalanceIQ - Setup & Run

## Prerequisites
- Python 3.10+
- Node.js 18+
- npm 9+
- Angular 20

## First Time Setup

### Backend
```bash
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### Frontend
```bash
cd frontend
npm install
```

### Environment
```bash
cp backend/.env.example backend/.env
```

## Run

### Backend
```bash
cd backend
venv\Scripts\activate
uvicorn app.main:app --reload
```
→ http://localhost:8000/api/docs

### Frontend
```bash
cd frontend
ng serve
```
→ http://localhost:4200
