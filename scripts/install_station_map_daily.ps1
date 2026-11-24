$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$python = Join-Path $root '.venv\Scripts\pythonw.exe'
$worker = Join-Path $PSScriptRoot 'run_station_map_daily.py'
$daily = Join-Path $root 'data\operational\station_map_web\daily'
$taskName = 'PBL6-DailyRainfall'
if (-not (Test-Path -LiteralPath $python) -or -not (Test-Path -LiteralPath $worker)) {
    throw 'The project Python environment and forecast runner must exist.'
}
if ((Get-TimeZone).GetUtcOffset((Get-Date)).TotalHours -ne 7) {
    throw 'The workstation must use UTC+7 for these local clock triggers.'
}
$arguments = '-X utf8 "' + $worker + '" --job auto'
$existing = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
if ($existing -and ($existing.Actions.Execute -ne $python -or $existing.Actions.Arguments -ne $arguments)) {
    throw 'A task with this name already points to another runner.'
}
$action = New-ScheduledTaskAction -Execute $python -Argument $arguments -WorkingDirectory $root
$triggers = @(
    (New-ScheduledTaskTrigger -Daily -At (Get-Date -Hour 18 -Minute 40 -Second 0)),
    (New-ScheduledTaskTrigger -Daily -At (Get-Date -Hour 20 -Minute 5 -Second 0))
)
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 25) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
$identity = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
$principal = New-ScheduledTaskPrincipal -UserId $identity -LogonType Interactive -RunLevel Limited
$registration = @{
    TaskName = $taskName
    Action = $action
    Trigger = $triggers
    Settings = $settings
    Principal = $principal
    Description = 'PBL6 local rainfall collection and delayed verification'
    Force = $true
}
$null = Register-ScheduledTask @registration
$task = Get-ScheduledTask -TaskName $taskName
$info = Get-ScheduledTaskInfo -TaskName $taskName
$record = [ordered]@{
    registered_at = [DateTimeOffset]::Now.ToString('o')
    task_state = $task.State.ToString()
    next_run_local = [DateTimeOffset]::new($info.NextRunTime).ToString('o')
    forecast_at = '18:40'
    verification_at = '20:05'
    interactive_user_required = $true
}
[void][IO.Directory]::CreateDirectory($daily)
$temporary = Join-Path $daily 'schedule.new.json'
[IO.File]::WriteAllText($temporary, ($record | ConvertTo-Json), [Text.UTF8Encoding]::new($false))
Move-Item -LiteralPath $temporary -Destination (Join-Path $daily 'schedule.json') -Force
$record | ConvertTo-Json -Compress
