$ErrorActionPreference = "SilentlyContinue"

$TaskName = "CourseResearchAgentWeb"

schtasks.exe /End /TN $TaskName | Out-Null
schtasks.exe /Delete /TN $TaskName /F | Out-Null

$Connections = Get-NetTCPConnection -LocalPort 8899 -State Listen
foreach ($Connection in $Connections) {
    Stop-Process -Id $Connection.OwningProcess -Force
}

$ExistingLaunchers = Get-CimInstance Win32_Process -Filter "Name = 'pythonw.exe'" -ErrorAction SilentlyContinue |
    Where-Object { $_.CommandLine -like "*run_web_ui_hidden.py*" }
foreach ($Launcher in $ExistingLaunchers) {
    Stop-Process -Id $Launcher.ProcessId -Force -ErrorAction SilentlyContinue
}
