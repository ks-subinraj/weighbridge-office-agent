@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "$p=Get-CimInstance Win32_Process -Filter \"Name='wb_agent.exe'\" | Where-Object { $_.ParentProcessId -notin @(Get-CimInstance Win32_Process -Filter \"Name='wb_agent.exe'\" | Select-Object -ExpandProperty ProcessId) }; $p | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }"
exit /b 0