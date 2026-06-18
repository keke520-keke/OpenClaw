@echo off
cd /d "C:\Users\24763\OpenClaw\backend"
python -m uvicorn main:app --host 0.0.0.0 --port 8000
pause
