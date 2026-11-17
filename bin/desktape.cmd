@echo off
rem desktape's command for agents (agent-efficiency D2): runs desktape.py from the plugin's folder.
setlocal
where uv >nul 2>nul
if %errorlevel%==0 (set "UV=uv" & goto run)
if exist "%USERPROFILE%\.local\bin\uv.exe" (set "UV=%USERPROFILE%\.local\bin\uv.exe" & goto run)
rem install-cold-read: winget links uv here, on the PATH of new shells only
if exist "%LOCALAPPDATA%\Microsoft\WinGet\Links\uv.exe" (set "UV=%LOCALAPPDATA%\Microsoft\WinGet\Links\uv.exe" & goto run)
echo desktape: uv is not installed (it brings Python and PyYAML): winget install --id astral-sh.uv -e, then restart Claude. See https://docs.astral.sh/uv/ 1>&2
exit /b 127
:run
"%UV%" run --quiet "%~dp0..\desktape.py" %*
exit /b %errorlevel%
