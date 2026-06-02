$token = Get-Content 'C:\Users\qw\.openclaw\gateway.token'
$ws = New-Object System.Net.WebSockets.ClientWebSocket
$ct = [Threading.CancellationToken]::None
$ws.ConnectAsync('ws://127.0.0.1:18789', $ct).Wait()
$msg = '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":1,"clientInfo":{"name":"test","version":"1.0"}}}'
$ws.SendAsync([ArraySegment[byte]][Text.Encoding]::UTF8.GetBytes($msg), 'Text', $true, $ct).Wait()
$buf = [byte[]]::new(4096)
$ws.ReceiveAsync([ArraySegment[byte]]$buf, $ct).Wait()
$ws.CloseAsync('NormalClosure', '', $ct).Wait()
[Text.Encoding]::UTF8.GetString($buf).Trim([char]0)
