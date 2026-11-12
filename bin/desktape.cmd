@echo off
rem desktape's command for agents (agent-efficiency D2): runs desktape.py from the plugin's folder.
where uv >nul 2>nul
if %errorlevel%==0 (
  uv run --quiet "%~dp0..\desktape.py" %*
) else (
  "%USERPROFILE%\.local\bin\uv.exe" run --quiet "%~dp0..\desktape.py" %*
)
exit /b %errorlevel%
