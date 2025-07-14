<powershell>
$ErrorActionPreference = "Stop"
Start-Transcript -Path "C:\user_data.log" -Append

Write-Host "---- Starting Windows EC2 user_data ----"

# --- Wait for network stack to initialize ---
Write-Host "Waiting for network..."
Start-Sleep -Seconds 30

# --- Set Admin password ---
Write-Host "Setting Administrator password..."
try {
    $AdminPassword = ConvertTo-SecureString "${admin_password}" -AsPlainText -Force
    Set-LocalUser -Name "Administrator" -Password $AdminPassword
    Set-LocalUser -Name "Administrator" -PasswordNeverExpires $true
} catch {
    Write-Host "❌ Failed to set admin password: $_"
}

# --- Generate self-signed cert ---
Write-Host "Generating self-signed cert..."
try {
    $cert = New-SelfSignedCertificate -DnsName $env:COMPUTERNAME -CertStoreLocation Cert:\LocalMachine\My
    $pwd = ConvertTo-SecureString -String "P@ssword123" -AsPlainText -Force
    Export-PfxCertificate -Cert $cert -FilePath "C:\winrm.pfx" -Password $pwd
} catch {
    Write-Host "❌ Failed to create/export cert: $_"
}

# --- Configure WinRM ---
Write-Host "Configuring WinRM..."
try {
    winrm quickconfig -force
    Set-Item -Path WSMan:\localhost\Service\Auth\Basic -Value $true
    Set-Item -Path WSMan:\localhost\Service\AllowUnencrypted -Value $true
    Set-Item -Path WSMan:\localhost\Client\TrustedHosts -Value "*" -Force
} catch {
    Write-Host "❌ WinRM setup failed: $_"
}

# --- Set DNS to DC1 ---
Write-Host "Setting static DNS..."
try {
    $adapter = Get-NetAdapter | Where-Object { $_.Status -eq 'Up' } | Select-Object -First 1
    Set-DnsClientServerAddress -InterfaceIndex $adapter.InterfaceIndex -ServerAddresses ("10.100.0.2")
} catch {
    Write-Host "❌ DNS config failed: $_"
}

# --- Setup HTTPS WinRM listener ---
Write-Host "Creating HTTPS WinRM listener..."
try {
    $thumb = $cert.Thumbprint
    Get-ChildItem WSMan:\Localhost\Listener | Where-Object { $_.Keys -like '*Transport=HTTPS*' } | Remove-Item -Force -ErrorAction SilentlyContinue
    winrm create winrm/config/Listener?Address=*+Transport=HTTPS "@{Hostname=`"$env:COMPUTERNAME`"; CertificateThumbprint=`"$thumb`"}"
} catch {
    Write-Host "❌ HTTPS listener creation failed: $_"
}

# --- Open Firewall Ports ---
Write-Host "Creating firewall rules..."
$ports = @(
    @{ Name = "WinRM HTTP";  Port = 5985 },
    @{ Name = "WinRM HTTPS"; Port = 5986 },
    @{ Name = "RDP";         Port = 3389 }
)
foreach ($rule in $ports) {
    try {
        New-NetFirewallRule -DisplayName $rule.Name -Direction Inbound -Action Allow -Protocol TCP -LocalPort $rule.Port
    } catch {
        Write-Host "❌ Failed to create firewall rule for $($rule.Port): $_"
    }
}

# --- Restart WinRM ---
Write-Host "Restarting WinRM..."
try {
    Restart-Service winrm -Force
} catch {
    Write-Host "❌ WinRM restart failed: $_"
}

Write-Host "✅ Finished user_data setup"
Stop-Transcript
</powershell>
