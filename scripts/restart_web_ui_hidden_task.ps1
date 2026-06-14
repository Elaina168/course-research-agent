$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$TaskName = "CourseResearchAgentWeb"
$PythonwExe = Join-Path $ProjectRoot ".venv\Scripts\pythonw.exe"
$HiddenLauncher = Join-Path $PSScriptRoot "run_web_ui_hidden.py"
$TaskRun = "`"$PythonwExe`" `"$HiddenLauncher`""
$StartTime = (Get-Date).AddMinutes(5).ToString("HH:mm")

if (-not (Test-Path $PythonwExe)) {
    throw "Missing virtual environment Python: $PythonwExe. Run: python -m venv .venv; .\.venv\Scripts\Activate.ps1; pip install -r requirements.txt"
}

if (-not (Test-Path $HiddenLauncher)) {
    throw "Missing hidden launcher: $HiddenLauncher"
}

schtasks.exe /End /TN $TaskName 2>$null | Out-Null

$Connections = Get-NetTCPConnection -LocalPort 8899 -State Listen -ErrorAction SilentlyContinue
foreach ($Connection in $Connections) {
    Stop-Process -Id $Connection.OwningProcess -Force -ErrorAction SilentlyContinue
}

$ExistingLaunchers = Get-CimInstance Win32_Process -Filter "Name = 'pythonw.exe'" -ErrorAction SilentlyContinue |
    Where-Object { $_.CommandLine -like "*run_web_ui_hidden.py*" }
foreach ($Launcher in $ExistingLaunchers) {
    Stop-Process -Id $Launcher.ProcessId -Force -ErrorAction SilentlyContinue
}

schtasks.exe /Delete /TN $TaskName /F 2>$null | Out-Null
schtasks.exe /Create /TN $TaskName /SC ONCE /ST $StartTime /TR $TaskRun /F | Out-Null
schtasks.exe /Run /TN $TaskName | Out-Null

Start-Sleep -Seconds 3

$Response = Invoke-WebRequest -UseBasicParsing http://localhost:8899/ -TimeoutSec 5
if ($Response.StatusCode -ne 200) {
    throw "Web UI did not return HTTP 200."
}

Write-Host "Course Research Agent Web UI is running at http://localhost:8899/"
