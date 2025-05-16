# === CONFIG ===
# $exePath = "python"
# $exeArgs = @("power_flow_test.py", "--scenario", "base_scenario.toml", "--params", "--show=false", "--force-active=true")
$exePath = "C:\Program Files\MATLAB\R2022a\bin\matlab.exe"
$exeArgs = @("-nosplash", "-batch", "run('.\ansto_case.m')")
# ==============

$startTime = Get-Date
$proc = Start-Process -FilePath $exePath -ArgumentList $exeArgs -PassThru
$peakMemory = 0

while (-not $proc.HasExited) {
    Start-Sleep -Milliseconds 50
    try {
        $current = Get-Process -Id $proc.Id -ErrorAction Stop
        $memUsage = $current.WorkingSet64 / 1MB
        if ($memUsage -gt $peakMemory) {
            $peakMemory = $memUsage
        }
    } catch {
        break
    }
}

$endTime = Get-Date
$duration = $endTime - $startTime

Write-Output "Runtime: $($duration.TotalMilliseconds) ms"
Write-Output ("Peak Memory Usage: {0:N2} MB" -f $peakMemory)
