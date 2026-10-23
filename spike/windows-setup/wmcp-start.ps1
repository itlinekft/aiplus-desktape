$d = Join-Path $env:USERPROFILE 'desktape'
$env:ANONYMIZED_TELEMETRY = 'false'
$env:WINDOWS_MCP_AUTH_KEY = (Get-Content (Join-Path $d 'wmcp-key.txt') -Raw).Trim()
$env:WINDOWS_MCP_TOOLS = 'Snapshot,Screenshot,Click,Type,Scroll,Shortcut,Move,Wait,WaitFor,App'
& (Join-Path $env:USERPROFILE '.local\bin\windows-mcp.exe') serve --transport streamable-http --host 127.0.0.1 --port 8000 *> (Join-Path $d 'wmcp.log')
