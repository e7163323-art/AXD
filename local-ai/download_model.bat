@echo off
chcp 65001 >nul
REM הורדה ידנית של המודל המומלץ (אם ההורדה בתוך התוכנה לא עובדת). אפשר לעצור ולהמשיך.
cd /d "%~dp0"
if not exist models mkdir models
echo מוריד את Qwen2.5-Coder 32B (כ-20GB) לתיקייה models ...
curl.exe -L -C - --retry 20 -o "models\Qwen2.5-Coder-32B-Instruct-Q4_K_M.gguf" "https://huggingface.co/bartowski/Qwen2.5-Coder-32B-Instruct-GGUF/resolve/main/Qwen2.5-Coder-32B-Instruct-Q4_K_M.gguf?download=true"
echo.
echo סיום. עכשיו פתח את Gaon.exe
pause
