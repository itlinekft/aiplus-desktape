# desktape panel-live: the screen as an MJPEG stream on this computer's loopback, for one viewer.
# Started in the person's desktop session by a one-off /it task (an SSH session cannot capture the screen);
# ends when its viewer disconnects, after 15 s when none connects, and after an hour at most (the panel
# starts a new one). ASCII only (PowerShell 5.1).
param([int]$Port = 48650, [int]$Fps = 10, [int]$Width = 1280, [int]$Quality = 6)
$ff = Get-ChildItem (Join-Path $env:LOCALAPPDATA 'Microsoft\WinGet\Packages') -Recurse -Filter ffmpeg.exe -ErrorAction SilentlyContinue | Select -First 1
if (-not $ff) { exit 2 }
$d = Join-Path $env:USERPROFILE 'desktape'; New-Item -ItemType Directory -Force $d | Out-Null
$vf = "scale='min($Width,iw)':-2"
& $ff.FullName -hide_banner -loglevel error -fflags nobuffer -f gdigrab -framerate $Fps -draw_mouse 1 -i desktop -vf $vf -c:v mjpeg -q:v $Quality -t 3600 -flush_packets 1 -f mjpeg "tcp://127.0.0.1:$($Port)?listen=1&listen_timeout=15000" *> (Join-Path $d 'live-stream.log')
