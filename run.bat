@echo off
REM Run DishaSetu backend on port 8000 (frontend expects this port)
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
