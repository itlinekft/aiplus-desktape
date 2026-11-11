# desktape panel-live: the screen as an MJPEG stream on this computer's loopback, for one viewer.
# Started in the person's desktop session by a one-off /it task (an SSH session cannot capture the screen);
# ends when its viewer disconnects, after 15 s when none connects, and after an hour at most (the panel
# starts a new one). ASCII only (PowerShell 5.1).
param([int]$Port = 48650, [int]$Fps = 10, [int]$Width = 1280, [int]$Quality = 6, [string]$Codec = 'mjpeg')
$ff = Get-ChildItem (Join-Path $env:LOCALAPPDATA 'Microsoft\WinGet\Packages') -Recurse -Filter ffmpeg.exe -ErrorAction SilentlyContinue | Select -First 1
if (-not $ff) { exit 2 }
$d = Join-Path $env:USERPROFILE 'desktape'; New-Item -ItemType Directory -Force $d | Out-Null
$vf = "scale='min($Width,iw)':-2"
# h264 (panel-live D8): only what changed goes out, no B-frames or look-ahead, and a rate ceiling so a busy screen
# cannot build a backlog on a slow network; the panel decodes it on its own side.
if ($Codec -eq 'h264') {
    $enc = @('-c:v', 'libx264', '-preset', 'ultrafast', '-tune', 'zerolatency', '-pix_fmt', 'yuv420p', '-crf', '23',
             '-maxrate', '4M', '-bufsize', '1M', '-g', [string]($Fps * 10), '-f', 'h264')
} else {
    $enc = @('-c:v', 'mjpeg', '-q:v', [string]$Quality, '-f', 'mjpeg')
}
& $ff.FullName -hide_banner -loglevel error -fflags nobuffer -f gdigrab -framerate $Fps -draw_mouse 1 -i desktop -vf $vf @enc -t 3600 -flush_packets 1 "tcp://127.0.0.1:$($Port)?listen=1&listen_timeout=15000" *> (Join-Path $d 'live-stream.log')
