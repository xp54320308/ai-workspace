$configPath = "C:\Users\qw\.acpx\config.json"
$json = Get-Content $configPath -Raw
$utf8 = New-Object System.Text.UTF8Encoding $false
[System.IO.File]::WriteAllText($configPath, $json, $utf8)
