@echo off
setlocal
cd /d "%~dp0"
set SHORTCUT=%USERPROFILE%\Desktop\Antigravity Session Patcher.lnk
powershell -NoProfile -ExecutionPolicy Bypass -Command "$shell=New-Object -ComObject WScript.Shell; $sc=$shell.CreateShortcut('%SHORTCUT%'); $sc.TargetPath=(Join-Path (Get-Location) 'start_antigravity_session_patcher.bat'); $sc.WorkingDirectory=(Get-Location).Path; $sc.Description='Antigravity Session Patcher Web UI'; $icon=Join-Path $env:LOCALAPPDATA 'Programs\antigravity\Antigravity.exe'; if(Test-Path $icon){$sc.IconLocation=$icon + ',0'}; $sc.Save()"
echo Desktop shortcut created: %SHORTCUT%
pause
