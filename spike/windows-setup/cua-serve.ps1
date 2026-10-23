$env:CUA_DRIVER_RS_TELEMETRY_ENABLED = 'false'; $env:DO_NOT_TRACK = '1'; $env:CUA_DRIVER_RS_UPDATE_CHECK = 'false'; $env:CUA_DRIVER_DISABLE_RUN_SCRIPT = '1'
$ff = Get-ChildItem (Join-Path $env:LOCALAPPDATA 'Microsoft\WinGet\Packages') -Recurse -Filter ffmpeg.exe -ErrorAction SilentlyContinue | Select -First 1
if ($ff) { $env:PATH = $ff.DirectoryName + ';' + $env:PATH }
$exe = Join-Path $env:USERPROFILE '.cua-driver\packages\releases\0.34.1-x86_64-pc-windows-msvc\cua-driver.exe'
& $exe serve --socket '\\.\pipe\cua-driver' *> (Join-Path $env:USERPROFILE 'meres\cua-serve.log')
