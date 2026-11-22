# desktape: set up this Windows computer as a desktape target, in one run (target-installer).
#
# Run it in your own desktop session, NOT as administrator. It asks for one UAC approval itself, and only when the
# SSH server, its firewall rule or an administrator's key file needs it. `desktape pair NAME --os windows` on the
# controller prints the command that downloads this file, checks its SHA-256 and runs it.
#
#   powershell -NoProfile -ExecutionPolicy Bypass -File setup-target.ps1 -Pair <base64 line> [-DryRun|-Yes] [-KeepAwake]
#
# -Pair      the controller's pairing line, base64-encoded (PowerShell 5.1 mangles quotes on a command line)
# -DryRun    print what would be done and change nothing
# -Yes       run the plan without asking (an agent that has shown the dry run's plan and got the person's yes);
#            without it the script prints the plan and asks once, in this window
# -KeepAwake also set sleep and monitor timeouts on mains power to never (the old values go into the report)
# -KeepFirewall leave the SSH firewall rule as it is (a VM behind a port forward, where the controller's packets
#            arrive from the host, not from the local subnet)
#
# What it does, each step skipped when it is already in place:
#   1. OpenSSH Server (Microsoft's optional feature), automatic start, firewall rule limited to the local subnet and
#      the controller's own addresses from the line   [elevated]
#   2. the controller's one line: the user's authorized_keys, or administrators_authorized_keys for an
#      administrator   [elevated for an administrator]
#   3. Cua Driver 0.55.0 from the pinned GitHub release: its install.ps1 and the helper module it loads
#      (_install-common.psm1, from the release's git tag) checked against the SHA-256s below; a running older
#      driver daemon stopped first; telemetry off, nothing connected to other AI tools   [this session, not elevated]
#   4. ffmpeg (Gyan.FFmpeg) through winget, in this user's account
#   5. only with -KeepAwake: sleep and monitor timeouts on mains power
# It ends with the report the person passes back to the controller. Log: %USERPROFILE%\desktape\setup-target.log.
# ASCII only: PowerShell 5.1 reads a BOM-less file as ANSI.

param(
    [Parameter(Mandatory = $true)][string]$Pair,
    [switch]$DryRun,
    [switch]$Yes,
    [switch]$KeepAwake,
    [switch]$KeepFirewall,
    [switch]$ElevatedPart
)

$ErrorActionPreference = 'Stop'
$CuaVersion = '0.55.0'
$CuaRelease = "https://github.com/trycua/cua/releases/download/cua-driver-rs-v$CuaVersion"
$CuaInstallSha = '8cdb0bffbe73e421fe81ecaf87d4fefeddcc0a36836d412dac5a78d0d797f2c4'
# install.ps1 loads this module from its own folder, else from cua.ai unpinned: it is not a release asset (driver-054 D7)
$CuaCommonUrl = "https://raw.githubusercontent.com/trycua/cua/cua-driver-rs-v$CuaVersion/libs/cua-driver/scripts/_install-common.psm1"
$CuaCommonSha = '99f34a84ceab04d4b488b1db4d71536c7a7ac7e645ac2ec295b4fd85244085b6'
$PairOpts = 'no-port-forwarding,no-agent-forwarding,no-X11-forwarding,no-pty'
$AdminKeys = Join-Path $env:ProgramData 'ssh\administrators_authorized_keys'
$ElevatedLog = Join-Path $env:ProgramData 'desktape\setup-target-elevated.log'

function Fail([string]$why) {
    Write-Host "STOP: $why"
    Write-Host 'Nothing more was changed. Tell the person, and pass this line to the controller.'
    exit 1
}

function Test-Pairable([string]$ip) {
    $o = $ip.Split('.')
    if ($o.Count -ne 4) { return $false }
    foreach ($x in $o) { if ($x -notmatch '^\d{1,3}$' -or [int]$x -gt 255) { return $false } }
    $a = [int]$o[0]; $b = [int]$o[1]
    if ($a -eq 10) { return $true }
    if ($a -eq 172 -and $b -ge 16 -and $b -le 31) { return $true }
    if ($a -eq 192 -and $b -eq 168) { return $true }
    if ($a -eq 100 -and $b -ge 64 -and $b -le 127) { return $true }     # VPN (shared address space, Tailscale)
    return $false
}

function Read-PairLine([string]$b64) {
    try { $line = [Text.Encoding]::ASCII.GetString([Convert]::FromBase64String($b64.Trim())).Trim() }
    catch { Fail '-Pair is not base64. Copy the whole command again from the controller.' }
    $re = '^from="([0-9.,]+)",' + [regex]::Escape($PairOpts) +
          ' ssh-ed25519 ([A-Za-z0-9+/]+=*) (desktape-pair-([A-Za-z0-9_.-]+)@[A-Za-z0-9_.-]+)$'
    $m = [regex]::Match($line, $re)
    if (-not $m.Success) { Fail "not a desktape pairing line: from=""<addresses>"",$PairOpts ssh-ed25519 <key> desktape-pair-<name>@<controller>" }
    $addrs = $m.Groups[1].Value.Split(',')
    foreach ($ip in $addrs) { if (-not (Test-Pairable $ip)) { Fail "$ip in from= is not a local-network or VPN address" } }
    $raw = [Convert]::FromBase64String($m.Groups[2].Value)
    if ([Text.Encoding]::ASCII.GetString($raw, 4, 11) -ne 'ssh-ed25519') { Fail 'the key inside is not an ed25519 key' }
    $sha = [Security.Cryptography.SHA256]::Create().ComputeHash($raw)
    $fp = 'SHA256:' + [Convert]::ToBase64String($sha).TrimEnd('=')
    $vpn = @($addrs | Where-Object { $_ -like '100.*' })
    return @{ Line = $line; Addrs = $addrs; Vpn = $vpn; Fp = $fp; Comment = $m.Groups[3].Value; Name = $m.Groups[4].Value }
}

function Test-Admin {
    return [bool](& whoami /groups | Select-String -SimpleMatch 'S-1-5-32-544')
}

function Test-Elevated {
    $p = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
    return $p.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Test-KeyIn([string]$file, [string]$comment) {
    if (-not (Test-Path $file)) { return $false }
    return [bool](Get-Content $file -ErrorAction SilentlyContinue | Where-Object { $_.Trim().EndsWith(' ' + $comment) })
}

function Add-KeyLine([string]$file, [string]$line) {
    $dir = Split-Path $file
    if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Force $dir | Out-Null }
    $text = ''
    if (Test-Path $file) { $text = [IO.File]::ReadAllText($file) }
    if ($text.Length -gt 0 -and -not $text.EndsWith("`n")) { $text += "`r`n" }
    [IO.File]::WriteAllText($file, $text + $line + "`r`n", (New-Object Text.ASCIIEncoding))
}

function Get-FirewallScope {
    $r = Get-NetFirewallRule -Name 'OpenSSH-Server-In-TCP' -ErrorAction SilentlyContinue
    if (-not $r) { return $null }
    return @(($r | Get-NetFirewallAddressFilter).RemoteAddress)
}

function Want-FirewallScope($info) {
    # the controller's own addresses from from= too: a VM behind a port forward sees the controller from outside its
    # local subnet, and LocalSubnet alone would lock it out (target-installer D1)
    return @(@('LocalSubnet') + $info.Addrs | Select-Object -Unique)
}

function Get-SshState($info) {
    $svc = Get-Service sshd -ErrorAction SilentlyContinue
    $scope = Get-FirewallScope
    $want = Want-FirewallScope $info
    $scopeOk = $false
    if ($scope) {
        $missing = @($info.Addrs | Where-Object { $scope -notcontains $_ })
        $scopeOk = ($scope -notcontains 'Any') -and ($missing.Count -eq 0)
    }
    if ($KeepFirewall) { $scopeOk = $true }
    return @{
        Installed = [bool]$svc
        Running   = [bool]($svc -and $svc.Status -eq 'Running')
        Automatic = [bool]($svc -and $svc.StartType -eq 'Automatic')
        Scope     = $scope
        ScopeOk   = $scopeOk
    }
}

function Find-Ffmpeg {
    $pkgs = Join-Path $env:LOCALAPPDATA 'Microsoft\WinGet\Packages'
    $hit = Get-ChildItem -Path $pkgs -Filter 'ffmpeg.exe' -Recurse -ErrorAction SilentlyContinue |
           Where-Object { $_.FullName -like '*Gyan.FFmpeg*\bin\ffmpeg.exe' } | Select-Object -First 1
    if ($hit) { return $hit.FullName }
    $cmd = Get-Command ffmpeg -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    return $null
}

function Get-CuaExe {
    $arch = 'x86_64'
    if ($env:PROCESSOR_ARCHITECTURE -eq 'ARM64') { $arch = 'aarch64' }
    return Join-Path $env:USERPROFILE ".cua-driver\packages\releases\$CuaVersion-$arch-pc-windows-msvc\cua-driver.exe"
}

function Get-CuaState {
    $exe = Get-CuaExe
    if (-not (Test-Path $exe)) { return $null }
    try { $v = (& $exe --version 2>&1 | Out-String).Trim() } catch { $v = '' }
    if ($v -notmatch [regex]::Escape($CuaVersion)) { return $null }
    return $exe
}

# ---- the elevated part: SSH server, its firewall rule, an administrator's key (the UAC child runs only this) ----

function Invoke-ElevatedPart($info) {
    $out = New-Object Collections.Generic.List[string]
    $st = Get-SshState $info
    if (-not $st.Installed) {
        Add-WindowsCapability -Online -Name 'OpenSSH.Server~~~~0.0.1.0' | Out-Null
        $out.Add('ssh: OpenSSH Server installed')
    }
    if (-not (Get-SshState $info).Automatic) { Set-Service sshd -StartupType Automatic; $out.Add('ssh: start automatic') }
    if (-not (Get-SshState $info).Running) { Start-Service sshd; $out.Add('ssh: sshd started') }
    $scope = Get-FirewallScope
    if ($null -eq $scope) {
        $out.Add('firewall: no OpenSSH-Server-In-TCP rule; left as it is (check the firewall by hand)')
    } elseif (-not (Get-SshState $info).ScopeOk) {
        $want = Want-FirewallScope $info
        if ($scope -contains 'Any') { $new = $want } else { $new = @($scope + $info.Addrs | Select-Object -Unique) }
        Set-NetFirewallRule -Name 'OpenSSH-Server-In-TCP' -RemoteAddress $new
        $out.Add('firewall: OpenSSH-Server-In-TCP was ' + ($scope -join ',') + ', now ' + ($new -join ','))
    }
    if ((Test-Admin) -and -not (Test-KeyIn $AdminKeys $info.Comment)) {
        Add-KeyLine $AdminKeys $info.Line
        # by SID: the group names are translated (a Hungarian Windows calls Administrators "Rendszergazdak"), measured
        $acl = & icacls $AdminKeys /inheritance:r /grant '*S-1-5-32-544:F' /grant '*S-1-5-18:F' 2>&1 | Out-String
        if ($LASTEXITCODE -ne 0) { throw "icacls on $AdminKeys failed: $($acl.Trim())" }
        $out.Add("key: added to $AdminKeys (only Administrators and SYSTEM may read it)")
    }
    return $out
}

if ($ElevatedPart) {
    $info = Read-PairLine $Pair
    New-Item -ItemType Directory -Force (Split-Path $ElevatedLog) | Out-Null
    try {
        $lines = Invoke-ElevatedPart $info
        Set-Content -Path $ElevatedLog -Value (@('ok') + $lines) -Encoding ASCII
        exit 0
    } catch {
        Set-Content -Path $ElevatedLog -Value @('failed', "$_") -Encoding ASCII
        exit 1
    }
}

# ---- the person's own session ----

$work = Join-Path $env:USERPROFILE 'desktape'
New-Item -ItemType Directory -Force $work | Out-Null
$log = Join-Path $work 'setup-target.log'
function Log([string]$s) { Write-Host $s; Add-Content -Path $log -Value ((Get-Date -Format 'HH:mm:ss') + ' ' + $s) -Encoding ASCII }
Set-Content -Path $log -Value ('desktape setup-target ' + (Get-Date -Format s)) -Encoding ASCII

$info = Read-PairLine $Pair
$lua = (Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System' -ErrorAction SilentlyContinue).EnableLUA
$uacOff = ($lua -eq 0)
$inline = $false
if ((Test-Elevated) -and $uacOff) {
    # measured on a test VM: with UAC off an administrator's every window is elevated, there is no other kind
    Write-Host 'Note: UAC is off on this computer, so this window is elevated like every other; no UAC prompt will come.'
    $inline = $true
} elseif ((Test-Elevated) -and $DryRun) {
    Write-Host 'Note: this window runs as administrator; the real run must be in a normal PowerShell window.'
} elseif (Test-Elevated) {
    Fail 'this window runs as administrator. Run it in a normal PowerShell window: Cua Driver installs in your own session, and the script asks for UAC itself when it needs it.'
}
$admin = Test-Admin
$os = Get-CimInstance Win32_OperatingSystem
$ips = @(Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
         Where-Object { $_.IPAddress -notlike '127.*' -and $_.IPAddress -notlike '169.254.*' } |
         Select-Object -ExpandProperty IPAddress)
$st = Get-SshState $info
$keyFile = Join-Path $env:USERPROFILE '.ssh\authorized_keys'
if ($admin) { $keyFile = $AdminKeys }
$keyThere = Test-KeyIn $keyFile $info.Comment
$cua = Get-CuaState
$oldCua = @(Get-Process -Name 'cua-driver', 'cua-driver-uia' -ErrorAction SilentlyContinue)
$ff = Find-Ffmpeg
$winget = [bool](Get-Command winget -ErrorAction SilentlyContinue)
$arm = ($env:PROCESSOR_ARCHITECTURE -eq 'ARM64')
$needUac = (-not $st.Installed) -or (-not $st.Running) -or (-not $st.Automatic) -or ($st.Scope -and -not $st.ScopeOk) -or ($admin -and -not $keyThere)

Log ''
Log "desktape target setup for '$($info.Name)' on $env:COMPUTERNAME ($($os.Caption) $($os.Version), $env:PROCESSOR_ARCHITECTURE)"
Log "user: $env:USERNAME (administrator: $(if ($admin) {'yes'} else {'no'}))   addresses: $($ips -join ', ')"
Log "the controller's key: $($info.Fp)  $($info.Comment)"
Log '  compare this fingerprint with the one on the controller screen.'
Log ''
Log 'Plan:'
$plan = @()
if (-not $st.Installed) { $plan += '  [UAC] install OpenSSH Server (Microsoft optional feature), start it, start automatically' }
elseif (-not ($st.Running -and $st.Automatic)) { $plan += '  [UAC] start sshd, and start it automatically' }
else { $plan += '  skip: SSH server installed and running' }
if ($KeepFirewall) { $plan += "  skip: firewall rule left as it is (-KeepFirewall): $($st.Scope -join ',')" }
elseif ($st.Scope -and -not $st.ScopeOk) { $plan += "  [UAC] firewall rule OpenSSH-Server-In-TCP: $($st.Scope -join ',') -> $((Want-FirewallScope $info) -join ',')" }
elseif ($st.Scope) { $plan += "  skip: firewall rule already limited ($($st.Scope -join ','))" }
if ($keyThere) { $plan += "  skip: the key is already in $keyFile" }
elseif ($admin) { $plan += "  [UAC] add the controller's line to $keyFile and set its permissions" }
else { $plan += "  add the controller's line to $keyFile" }
if ($arm) { $plan += '  skip: Cua Driver (an ARM PC; desktape is measured on x86_64 only)' }
elseif ($cua) { $plan += "  skip: Cua Driver $CuaVersion is installed" }
else {
    if ($oldCua.Count -gt 0) { $plan += "  stop the running Cua Driver (pid $(($oldCua | ForEach-Object { $_.Id }) -join ', ')); desktape starts the new one" }
    $plan += "  download Cua Driver $CuaVersion install.ps1 from github.com/trycua/cua (pinned release), check SHA-256 $CuaInstallSha, and its helper _install-common.psm1 from the release's tag, check SHA-256 $CuaCommonSha; run it with telemetry off, nothing connected"
}
if ($ff) { $plan += "  skip: ffmpeg found ($ff)" }
elseif ($winget) { $plan += '  winget install Gyan.FFmpeg (accepts winget''s source and package agreements)' }
else { $plan += '  skip: ffmpeg, winget is missing (install App Installer from the Microsoft Store, then run this again)' }
if ($KeepAwake) { $plan += '  sleep and monitor timeouts on mains power: never (old values in the report)' }
else { $plan += '  skip: screen timeouts left as they are (-KeepAwake changes them)' }
$plan | ForEach-Object { Log $_ }
if ($needUac -and $inline) { Log 'The [UAC] steps run in this window (UAC is off).' }
elseif ($needUac) { Log 'Windows asks for one UAC approval for the [UAC] steps; that approval is the person''s.' }
if ($DryRun) { Log ''; Log 'Dry run: nothing was changed.'; exit 0 }
if (-not $Yes) {
    $ans = ''
    try { $ans = Read-Host 'Run these steps? Type y and press Enter (anything else stops here)' } catch { $ans = '' }
    # [string]: Read-Host gives $null when stdin is closed (an agent's shell), and `$null -notmatch` is not $true
    if (-not ([string]$ans -match '^\s*(y|yes|i|igen)\s*$')) { Log 'Not confirmed: nothing was changed.'; exit 2 }
    if (-not $KeepAwake) {
        $ans = ''
        try { $ans = Read-Host 'Also keep this screen awake on mains power (sleep and monitor: never)? y/N' } catch { $ans = '' }
        if ([string]$ans -match '^\s*(y|yes|i|igen)\s*$') { $KeepAwake = [switch]$true }
    }
}
Log "confirmed: $(if ($Yes) {'-Yes'} else {'in this window'})"

$done = New-Object Collections.Generic.List[string]
$skipped = New-Object Collections.Generic.List[string]

# the user's own key file (a standard user's needs no elevation)
if (-not $admin -and -not $keyThere) {
    Add-KeyLine $keyFile $info.Line
    $done.Add("key: added to $keyFile")
}

# Cua Driver, in this session, not elevated
if (-not $arm -and -not $cua) {
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    $cuaDir = Join-Path $work 'cua-install'
    New-Item -ItemType Directory -Force $cuaDir | Out-Null
    $inst = Join-Path $cuaDir 'install.ps1'
    $common = Join-Path $cuaDir '_install-common.psm1'
    Invoke-WebRequest "$CuaRelease/install.ps1" -OutFile $inst -UseBasicParsing
    $h = (Get-FileHash $inst -Algorithm SHA256).Hash.ToLower()
    if ($h -ne $CuaInstallSha) { Fail "Cua Driver install.ps1 has SHA-256 $h, not ${CuaInstallSha}: not run" }
    Invoke-WebRequest $CuaCommonUrl -OutFile $common -UseBasicParsing
    $h = (Get-FileHash $common -Algorithm SHA256).Hash.ToLower()
    if ($h -ne $CuaCommonSha) { Fail "Cua Driver _install-common.psm1 has SHA-256 $h, not ${CuaCommonSha}: not run" }
    # The installer stops a running driver too, but an elevated one it cannot stop makes it ask on the console,
    # which nobody sees here (driver-054 D7): stop it first, and stop this script when it survives.
    $oldCua = @(Get-Process -Name 'cua-driver', 'cua-driver-uia' -ErrorAction SilentlyContinue)
    foreach ($p in $oldCua) {
        try { Stop-Process -Id $p.Id -Force -ErrorAction Stop; Log "stopped the running Cua Driver (pid $($p.Id))" }
        catch { Log "could not stop Cua Driver pid $($p.Id): $($_.Exception.Message)" }
    }
    Start-Sleep -Seconds 1
    $left = @(Get-Process -Name 'cua-driver', 'cua-driver-uia' -ErrorAction SilentlyContinue)
    if ($left.Count -gt 0) {
        Fail ("a Cua Driver runs elevated (pid $(($left | ForEach-Object { $_.Id }) -join ', ')) and this window cannot stop it; " +
              "as administrator run: taskkill /im cua-driver.exe /f   (or from the controller over SSH), then run this again")
    }
    $env:CUA_DRIVER_RS_VERSION = $CuaVersion; $env:CUA_DRIVER_RS_TELEMETRY_ENABLED = 'false'
    $env:DO_NOT_TRACK = '1'; $env:CUA_DRIVER_RS_UPDATE_CHECK = 'false'
    $env:CUA_DRIVER_RS_KEEP_VERSIONS = '0'          # keep older releases: going back is the profile's `driver:` line
    & powershell -NoProfile -ExecutionPolicy Bypass -File $inst -NoAutoStart -NoPathUpdate -NoConnect -NoTest | ForEach-Object { Add-Content -Path $log -Value "$_" -Encoding ASCII }
    $exe = Get-CuaExe
    if (-not (Test-Path $exe)) { Fail "the Cua Driver installer ran, but $exe is not there (see $log)" }
    & $exe telemetry disable | Out-Null
    # 0.55.0 has no `config set` keys for the update check and the script runner: desktape passes both as
    # environment variables whenever it starts the driver (DRIVER_ENV)
    $cua = Get-CuaState
    $done.Add("Cua Driver: $CuaVersion installed")
}

# ffmpeg, in this user's account
if (-not $ff -and $winget) {
    & winget install --id Gyan.FFmpeg -e --accept-source-agreements --accept-package-agreements | ForEach-Object { Add-Content -Path $log -Value "$_" -Encoding ASCII }
    $ff = Find-Ffmpeg
    if ($ff) { $done.Add("ffmpeg: installed ($ff)") } else { $skipped.Add("ffmpeg: winget ran, but no ffmpeg.exe was found (see $log)") }
} elseif (-not $ff) { $skipped.Add('ffmpeg: winget is missing') }

# the one UAC approval
if ($needUac -and $inline) {
    try { Invoke-ElevatedPart $info | ForEach-Object { $done.Add($_) } }
    catch { $skipped.Add("SSH server / firewall / admin key: $_") }
} elseif ($needUac) {
    Log 'Asking Windows for the UAC approval (SSH server, firewall, administrator key) ...'
    if (Test-Path $ElevatedLog) { Remove-Item $ElevatedLog -Force -ErrorAction SilentlyContinue }
    try {
        $childArgs = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', "`"$PSCommandPath`"", '-Pair', $Pair.Trim(), '-ElevatedPart')
        if ($KeepFirewall) { $childArgs += '-KeepFirewall' }
        $p = Start-Process powershell -Verb RunAs -Wait -PassThru -ArgumentList $childArgs
        $res = @()
        if (Test-Path $ElevatedLog) { $res = @(Get-Content $ElevatedLog) }
        if ($p.ExitCode -eq 0 -and $res.Count -gt 0 -and $res[0] -eq 'ok') { $res | Select-Object -Skip 1 | ForEach-Object { $done.Add($_) } }
        else { $skipped.Add('SSH server / firewall / admin key: the elevated part failed: ' + (($res | Select-Object -Skip 1) -join ' ')) }
    } catch {
        $skipped.Add('SSH server / firewall / admin key: UAC was not approved')
    }
}

# screen awake, only with -KeepAwake
$screen = 'left as it was'
if ($KeepAwake) {
    $before = (& powercfg /query SCHEME_CURRENT SUB_SLEEP STANDBYIDLE | Select-String 'AC Power Setting' | Out-String).Trim()
    & powercfg /change standby-timeout-ac 0
    & powercfg /change monitor-timeout-ac 0
    $screen = "sleep and monitor off on mains power (before: $before)"
}

# the report
$st = Get-SshState $info
$keyThere = Test-KeyIn $keyFile $info.Comment
$sig = 'not installed'
if ($cua) { $sig = (Get-AuthenticodeSignature $cua).Status }
$lan = @($ips | Where-Object { $_ -notlike '100.*' }) -join ', '
$vpnIp = @($ips | Where-Object { $_ -like '100.*' }) -join ', '
if (-not $vpnIp) { $vpnIp = 'none' }
$ffv = 'missing'
if ($ff) { $ffv = ((& $ff -version 2>&1 | Select-Object -First 1) -split ' ')[2] }
$keyLine = 'NOT in place'
if ($keyThere) { $keyLine = "$($info.Fp)  $($info.Comment)  in $keyFile" }
$sshLine = 'not running'
if ($st.Running) { $sshLine = 'running, firewall ' + ($st.Scope -join ',') }

Log ''
foreach ($d in $done) { Log "done: $d" }
foreach ($s in $skipped) { Log "skipped: $s" }
Log ''
Log '---- pass this to the controller ----'
Log "desktape target ready: $env:COMPUTERNAME"
Log "  OS:            $($os.Caption) $($os.Version) $env:PROCESSOR_ARCHITECTURE"
Log "  user:          $env:USERNAME  (administrator: $(if ($admin) {'yes'} else {'no'}))"
Log "  LAN address:   $lan      VPN address: $vpnIp"
Log "  key accepted:  $keyLine"
Log "  SSH server:    $sshLine"
Log "  Cua Driver:    $(if ($cua) {$CuaVersion} else {'missing'})  (signature: $sig)     ffmpeg: $ffv"
Log "  screen:        $screen"
Log "  skipped:       $(if ($skipped.Count) {$skipped -join '; '} else {'nothing'})"
$firstLan = @($ips | Where-Object { $_ -notlike '100.*' } | Select-Object -First 1)
Log "  next, on the controller: desktape.py pair $($info.Name) --host $env:USERNAME@$firstLan   then: desktape.py pair $($info.Name) --check"
Log '-------------------------------------'
if ($skipped.Count -gt 0 -or -not $keyThere -or -not $st.Running -or -not $cua) { exit 1 }
exit 0
