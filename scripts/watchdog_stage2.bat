@echo off
cd /d "D:\Major Project"
echo === watchdog started %date% %time% === >> logs\stage2.log
:loop
python -u scripts\build_models.py >> logs\stage2.log 2>&1
if errorlevel 1 (
  echo === watchdog resume after failure %date% %time% === >> logs\stage2.log
  timeout /t 3 /nobreak >nul
  goto loop
)
echo === stage 2 finished OK %date% %time% === >> logs\stage2.log
