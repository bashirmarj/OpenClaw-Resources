# Vectis Validation Lab

This is an isolated workbench for validating 3D CAD feature extraction against Analysis Situs ground truth.

## Structure
- `/backend`: FastAPI bridge that serves STEP files and AS logs.
- `/frontend`: React/Three.js viewer for 3D inspection.

## How to Run Locally

### 1. Requirements
- Python 3.10+
- Node.js 18+ (if building from source)

### 2. Setup Backend
```bash
cd lab/backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Run the Lab
```bash
cd lab/backend
python lab_bridge.py
```
The lab will be available at http://localhost:8000.

## Note on Resources
The backend expects the `Analysis Situs logs` folder to be present at `../../Analysis Situs logs` relative to the `lab/backend` directory (which it is in this repository).
