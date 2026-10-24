# desktape: type into a window through Windows itself (data-driven-import), for dialogs whose UI Automation
# does not answer. Runs as a one-off task in the desktop session. Reads os-input.json next to it:
#   {"title": "<window title>", "keys": "<SendKeys string>", "at": [fx, dy] or null}
# Brings the window to the front, checks that it IS the foreground window, clicks for real at `at` if given
# (fx: fraction of the window's width from its left edge; dy: pixels from its bottom edge if negative, else
# from its top), then sends the keys.
# Writes os-input-out.json: {"activated": bool, "front": "<title in front>", "sent": bool}.
# File mode, {"title": "<file dialog title>", "file": "<path>"}: the standard Windows file dialog's own
# controls, the same in every language: the file name box (control 1148) gets the path through WM_SETTEXT,
# is read back, and OK (control 1) is pressed. Writes {"found", "set", "closed", "front", "box", "message"}:
# "box" is the handle of a dialog of the same program that came up instead (Windows' own "path does not
# exist" box), "message" its Static texts, if it has any.
$ErrorActionPreference = 'Stop'
$dir = Split-Path -Parent $MyInvocation.MyCommand.Path
$req = Get-Content -Raw -Encoding UTF8 (Join-Path $dir 'os-input.json') | ConvertFrom-Json
Add-Type @"
using System; using System.Text; using System.Runtime.InteropServices;
public class W {
  [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
  [DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern int GetWindowText(IntPtr h, StringBuilder s, int n);
  [StructLayout(LayoutKind.Sequential)] public struct RECT { public int L, T, R, B; }
  [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECT r);
  [DllImport("user32.dll")] public static extern bool SetCursorPos(int x, int y);
  [DllImport("user32.dll")] public static extern void mouse_event(uint f, uint dx, uint dy, uint d, UIntPtr e);
  [DllImport("user32.dll")] public static extern bool SetProcessDPIAware();
  [DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern IntPtr FindWindow(string c, string t);
  [DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern IntPtr FindWindowEx(IntPtr p, IntPtr a, string c, string t);
  [DllImport("user32.dll")] public static extern IntPtr GetDlgItem(IntPtr h, int id);
  [DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern IntPtr SendMessage(IntPtr h, uint m, IntPtr w, string l);
  [DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern IntPtr SendMessage(IntPtr h, uint m, IntPtr w, StringBuilder l);
  [DllImport("user32.dll")] public static extern bool PostMessage(IntPtr h, uint m, IntPtr w, IntPtr l);
  [DllImport("user32.dll")] public static extern bool IsWindow(IntPtr h);
  [DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern int GetClassName(IntPtr h, StringBuilder s, int n);
  [DllImport("user32.dll")] public static extern int GetDlgCtrlID(IntPtr h);
  [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
  [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
  public delegate bool EnumProc(IntPtr h, IntPtr l);
  [DllImport("user32.dll")] public static extern bool EnumChildWindows(IntPtr p, EnumProc cb, IntPtr l);
  [DllImport("user32.dll")] public static extern bool EnumWindows(EnumProc cb, IntPtr l);
  public static System.Collections.Generic.List<IntPtr> SameProcessDialogs(IntPtr h) {
    uint me; GetWindowThreadProcessId(h, out me);
    var r = new System.Collections.Generic.List<IntPtr>();
    EnumWindows(delegate(IntPtr w, IntPtr l) {
      uint p; GetWindowThreadProcessId(w, out p);
      var c = new StringBuilder(64); GetClassName(w, c, 64);
      if (p == me && w != h && IsWindowVisible(w) && c.ToString() == "#32770") r.Add(w);
      return true; }, IntPtr.Zero);
    return r;
  }
  public static System.Collections.Generic.List<IntPtr> Descendants(IntPtr p) {
    var r = new System.Collections.Generic.List<IntPtr>();
    EnumChildWindows(p, delegate(IntPtr h, IntPtr l) { r.Add(h); return true; }, IntPtr.Zero);
    return r;
  }
}
"@
[void][W]::SetProcessDPIAware()     # physical pixels, as the driver reports them
function Front { $sb = New-Object System.Text.StringBuilder 512; [void][W]::GetWindowText([W]::GetForegroundWindow(), $sb, 512); $sb.ToString() }
function Text($h) { $sb = New-Object System.Text.StringBuilder 2048; [void][W]::SendMessage($h, 0x000D, [IntPtr]2048, $sb); $sb.ToString() }
function ClassOf($h) { $sb = New-Object System.Text.StringBuilder 256; [void][W]::GetClassName($h, $sb, 256); $sb.ToString() }
$out = Join-Path $dir 'os-input-out.json'

if ($req.file) {
  $h = [W]::FindWindow('#32770', $req.title)
  $r = @{ found = ($h -ne [IntPtr]::Zero); set = $false; closed = $false; front = ''; message = '' }
  if ($r.found) {
    # The file name box is control 1148 (a ComboBoxEx32 > ComboBox > Edit), nested below the dialog in the
    # Vista-style dialog, so GetDlgItem on the dialog does not see it: search every descendant.
    $all = [W]::Descendants($h)
    $box = $all | Where-Object { [W]::GetDlgCtrlID($_) -eq 1148 } | Select-Object -First 1
    $edit = [IntPtr]::Zero
    if ($box) {
      if ((ClassOf $box) -eq 'Edit') { $edit = $box }
      else { $edit = [W]::Descendants($box) | Where-Object { (ClassOf $_) -eq 'Edit' } | Select-Object -First 1 }
    }
    if (-not $edit) { $edit = [IntPtr]::Zero }
    if ($edit -eq [IntPtr]::Zero) {                        # say why: the dialog's controls, for the report
      $r.controls = @($all | ForEach-Object { '{0}#{1}' -f (ClassOf $_), [W]::GetDlgCtrlID($_) } | Select-Object -Unique -First 40) -join ' '
    }
    if ($edit -ne [IntPtr]::Zero -and (ClassOf $edit) -eq 'Edit') {
      [void][W]::SendMessage($edit, 0x000C, [IntPtr]::Zero, [string]$req.file)        # WM_SETTEXT
      $r.readback = Text $edit
      $r.set = ($r.readback -eq $req.file)
    }
    if ($r.set) {
      [void][W]::PostMessage([W]::GetDlgItem($h, 1), 0x00F5, [IntPtr]::Zero, [IntPtr]::Zero)   # BM_CLICK on OK
      for ($i = 0; $i -lt 20 -and [W]::IsWindow($h); $i++) { Start-Sleep -Milliseconds 150 }
      Start-Sleep -Milliseconds 300
      $r.closed = -not [W]::IsWindow($h)
      $r.front = Front
      # A message box of the same program that came up instead (Windows' own "path does not exist"): it is
      # another visible #32770 of that process. Quote its own words.
      foreach ($m in [W]::SameProcessDialogs($h)) {
        $t = @([W]::Descendants($m) | Where-Object { (ClassOf $_) -eq 'Static' } | ForEach-Object { (Text $_).Trim() } | Where-Object { $_ })
        # a task dialog draws its text itself; desktape reads it through the driver by this handle
        $r.box = [int64]$m
        $r.message = ($t -join ' / ') -replace '\s+', ' '
        break
      }
    }
  }
  $r | ConvertTo-Json -Compress | Set-Content -Encoding UTF8 $out
  exit 0
}

$shell = New-Object -ComObject WScript.Shell
$activated = $shell.AppActivate($req.title)
Start-Sleep -Milliseconds 400
$front = Front
$sent = $false
$clicked = $null
if ($front -eq $req.title) {
  if ($req.at) {
    $r = New-Object W+RECT; [void][W]::GetWindowRect([W]::GetForegroundWindow(), [ref]$r)
    $x = [int]($r.L + ($r.R - $r.L) * $req.at[0])
    $y = if ($req.at[1] -lt 0) { [int]($r.B + $req.at[1]) } else { [int]($r.T + $req.at[1]) }
    [void][W]::SetCursorPos($x, $y); Start-Sleep -Milliseconds 150
    [W]::mouse_event(0x0002, 0, 0, 0, [UIntPtr]::Zero); Start-Sleep -Milliseconds 60
    [W]::mouse_event(0x0004, 0, 0, 0, [UIntPtr]::Zero); Start-Sleep -Milliseconds 300
    $clicked = "$x,$y"
  }
  $shell.SendKeys($req.keys)
  $sent = $true
}
@{ activated = $activated; front = $front; sent = $sent; clicked = $clicked } | ConvertTo-Json -Compress |
  Set-Content -Encoding UTF8 $out
