$tokenPath = "C:\Users\qw\.openclaw\gateway.token"
$user = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
icacls $tokenPath /inheritance:r /grant:r ("$user`:R")
