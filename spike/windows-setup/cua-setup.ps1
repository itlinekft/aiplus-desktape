$d = Join-Path $env:USERPROFILE 'desktape'
$f = Join-Path $d 'cua-setup.log'
$env:CUA_DRIVER_RS_VERSION = '0.34.1'
$env:CUA_DRIVER_RS_TELEMETRY_ENABLED = 'false'
$env:DO_NOT_TRACK = '1'
$env:CUA_DRIVER_RS_UPDATE_CHECK = 'false'
$o = & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $d 'cua-install.ps1') -NoAutoStart -NoPathUpdate 2>&1 | % { "$_" }
$exe = Join-Path $env:LOCALAPPDATA 'Programs\Cua\cua-driver\bin\cua-driver.exe'
$o += "--- exe: $exe exists=$(Test-Path $exe)"
if (Test-Path $exe) {
  $o += & $exe --version 2>&1 | % { "$_" }
  $o += & $exe telemetry disable 2>&1 | % { "$_" }
  $o += & $exe config set update_check_enabled false 2>&1 | % { "$_" }
  $o += & $exe config set disable_run_script true 2>&1 | % { "$_" }
  $o += & $exe telemetry status --json 2>&1 | % { "$_" }
  $o += (Get-AuthenticodeSignature $exe | % { "sig: $($_.Status) $($_.SignerCertificate.Subject)" })
}
($o + 'done') | Set-Content -Encoding utf8 $f
