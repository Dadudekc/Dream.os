# Auto-elevate the script if not running as admin
function Ensure-RunAsAdmin {
    if (-NOT ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {
        $arguments = "& '" + $myinvocation.mycommand.definition + "'"
        Start-Process powershell -Verb runAs -ArgumentList $arguments
        exit
    }
}

Ensure-RunAsAdmin

Write-Output "Running as admin... Applying registry edits."

# Registry edit to show Console lock display off timeout
$regPath = "HKLM:\SYSTEM\CurrentControlSet\Control\Power\PowerSettings\238C9FA8-0AAD-41ED-83F4-97BE242C8F20\7bc4a2f9-d8fc-4469-b07b-33eb785aaca0"
Set-ItemProperty -Path $regPath -Name "Attributes" -Value 2 -Force

Write-Output "Registry updated successfully."

# Optional: Set the Console lock display off timeout to Never (0 minutes)
powercfg -change -monitor-timeout-ac 0
powercfg -change -monitor-timeout-dc 0

Write-Output "Monitor timeouts disabled."

# Optional: Disable sleep completely
powercfg -change -standby-timeout-ac 0
powercfg -change -standby-timeout-dc 0

Write-Output "Sleep disabled on AC and DC."

# Optional: Disable Hibernate
powercfg -hibernate off

Write-Output "Hibernate disabled."

# Optional: Disable screensaver via registry
Set-ItemProperty -Path "HKCU:\Control Panel\Desktop" -Name "ScreenSaveActive" -Value 0

Write-Output "Screensaver disabled."
