# Ensure Admin Rights
function Ensure-RunAsAdmin {
    if (-NOT ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {
        $arguments = "& '" + $myinvocation.mycommand.definition + "'"
        Start-Process powershell -Verb runAs -ArgumentList $arguments
        exit
    }
}

Ensure-RunAsAdmin

Write-Host "Applying system settings to prevent sleep/screensaver..."

# Registry edit to show Console lock display off timeout
$regPath = "HKLM:\SYSTEM\CurrentControlSet\Control\Power\PowerSettings\238C9FA8-0AAD-41ED-83F4-97BE242C8F20\7bc4a2f9-d8fc-4469-b07b-33eb785aaca0"
Set-ItemProperty -Path $regPath -Name "Attributes" -Value 2 -Force

# Disable monitor timeout
powercfg /change monitor-timeout-ac 0
powercfg /change monitor-timeout-dc 0

# Disable sleep
powercfg /change standby-timeout-ac 0
powercfg /change standby-timeout-dc 0

# Disable hibernate
powercfg -hibernate off

# Disable screensaver
Set-ItemProperty -Path "HKCU:\Control Panel\Desktop" -Name "ScreenSaveActive" -Value 0

Write-Host "Settings applied successfully."

# Anti-idle loop (mouse jiggle)
Write-Host "Starting anti-idle loop (Ctrl+C to stop in console)"
Add-Type -AssemblyName System.Windows.Forms

while ($true) {
    [System.Windows.Forms.Cursor]::Position = [System.Drawing.Point]::new(1,1)
    Start-Sleep -Milliseconds 100
    [System.Windows.Forms.Cursor]::Position = [System.Drawing.Point]::new(2,2)
    Start-Sleep -Seconds 50
}
