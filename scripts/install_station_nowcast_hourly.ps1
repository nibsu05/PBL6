$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$python = Join-Path $root '.venv\Scripts\pythonw.exe'
$worker = Join-Path $PSScriptRoot 'run_station_nowcast_hourly.py'
$state = Join-Path $root 'data\operational\station_map_web\hourly'
$taskName = 'PBL6-HourlyRainfall'
if (-not (Test-Path -LiteralPath $python) -or -not (Test-Path -LiteralPath $worker)) {
    throw 'The project Python environment and hourly runner must exist.'
}
if ((Get-TimeZone).GetUtcOffset((Get-Date)).TotalHours -ne 7) {
    throw 'The workstation must use UTC+7 for these local clock triggers.'
}

$arguments = '-X utf8 "' + $worker + '"'
$existing = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
if ($existing -and ($existing.Actions.Execute -ne $python -or $existing.Actions.Arguments -ne $arguments)) {
    throw 'A task with this name already points to another runner.'
}
$action = New-ScheduledTaskAction -Execute $python -Argument $arguments -WorkingDirectory $root
$triggers = @(0..23 | ForEach-Object {
    New-ScheduledTaskTrigger -Daily -At (Get-Date -Hour $_ -Minute 5 -Second 0)
})
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 12) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
$identity = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
$principal = New-ScheduledTaskPrincipal -UserId $identity -LogonType Interactive -RunLevel Limited
$registration = @{
    TaskName = $taskName
    Action = $action
    Trigger = $triggers
    Settings = $settings
    Principal = $principal
    Description = 'PBL6 hourly Da Nang rainfall pilot with delayed verification'
    Force = $true
}
$null = Register-ScheduledTask @registration

[void][IO.Directory]::CreateDirectory($state)
$display = Join-Path $state 'display.json'
if (-not (Test-Path -LiteralPath $display)) {
    [IO.File]::WriteAllText($display, '{"enabled":false}', [Text.UTF8Encoding]::new($false))
}
$info = Get-ScheduledTaskInfo -TaskName $taskName
$record = [ordered]@{
    task_name = $taskName
    registered_at = [DateTimeOffset]::Now.ToString('o')
    next_run_local = [DateTimeOffset]::new($info.NextRunTime).ToString('o')
    start_minute = 5
    deadline_minute = 15
    triggers_per_day = (Get-ScheduledTask -TaskName $taskName).Triggers.Count
}
$temporary = Join-Path $state 'schedule.new.json'
[IO.File]::WriteAllText($temporary, ($record | ConvertTo-Json), [Text.UTF8Encoding]::new($false))
Move-Item -LiteralPath $temporary -Destination (Join-Path $state 'schedule.json') -Force
$record | ConvertTo-Json -Compress
