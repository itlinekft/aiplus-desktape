# Runs inside the interactive session (scheduled task /IT). Reads meres\vez-cmd.json, writes
# meres\vez-out.txt and, for screenshots, meres\vez-shot.png. One action per run.
$ErrorActionPreference = 'Stop'
$d = Join-Path $env:USERPROFILE 'meres'
$out = Join-Path $d 'vez-out.txt'
try {
  Add-Type -AssemblyName System.Drawing, System.Windows.Forms, UIAutomationClient, UIAutomationTypes
  Add-Type @'
using System; using System.Runtime.InteropServices;
public static class W {
  [DllImport("user32.dll")] public static extern bool SetProcessDPIAware();
  [DllImport("user32.dll")] public static extern bool SetCursorPos(int x, int y);
  [DllImport("user32.dll")] public static extern void mouse_event(uint f, uint x, uint y, uint d, UIntPtr e);
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
}
'@
  [W]::SetProcessDPIAware() | Out-Null
  $c = Get-Content (Join-Path $d 'vez-cmd.json') -Raw | ConvertFrom-Json
  $r = @()
  switch ($c.a) {
    'shot' {
      $b = [System.Windows.Forms.SystemInformation]::VirtualScreen
      $bmp = New-Object System.Drawing.Bitmap $b.Width, $b.Height
      $g = [System.Drawing.Graphics]::FromImage($bmp)
      $g.CopyFromScreen($b.Left, $b.Top, 0, 0, $bmp.Size)
      $bmp.Save((Join-Path $d 'vez-shot.png'), [System.Drawing.Imaging.ImageFormat]::Png)
      $r += "shot $($b.Width)x$($b.Height) at $($b.Left),$($b.Top)"
    }
    'click' {
      [W]::SetCursorPos([int]$c.x, [int]$c.y) | Out-Null; Start-Sleep -Milliseconds 120
      $n = if ($c.n) { [int]$c.n } else { 1 }
      for ($i = 0; $i -lt $n; $i++) { [W]::mouse_event(2,0,0,0,[UIntPtr]::Zero); [W]::mouse_event(4,0,0,0,[UIntPtr]::Zero); Start-Sleep -Milliseconds 80 }
      $r += "clicked $($c.x),$($c.y) x$n"
    }
    'keys' { [System.Windows.Forms.SendKeys]::SendWait($c.k); $r += "keys sent" }
    'uia' {
      # Elements of the Claude window: name, control type, rectangle. Optional filter $c.f (substring).
      $root = [System.Windows.Automation.AutomationElement]::RootElement
      $cond = New-Object System.Windows.Automation.PropertyCondition ([System.Windows.Automation.AutomationElement]::NameProperty), 'Claude'
      $win = $root.FindFirst([System.Windows.Automation.TreeScope]::Children, $cond)
      if (-not $win) { $r += 'no Claude window' } else {
        $all = $win.FindAll([System.Windows.Automation.TreeScope]::Descendants, [System.Windows.Automation.Condition]::TrueCondition)
        foreach ($e in $all) {
          $nm = $e.Current.Name; if (-not $nm) { continue }
          if ($c.f -and $nm -notlike "*$($c.f)*") { continue }
          $re = $e.Current.BoundingRectangle; if ($re.IsEmpty) { continue }
          $r += "{0} | {1} | {2},{3} {4}x{5}" -f $nm.Substring(0,[Math]::Min(60,$nm.Length)), $e.Current.ControlType.ProgrammaticName.Replace('ControlType.',''), [int]$re.X, [int]$re.Y, [int]$re.Width, [int]$re.Height
          if ($r.Count -gt 300) { break }
        }
      }
    }
    'focus' {
      $p = Get-Process claude -ErrorAction SilentlyContinue | ? { $_.MainWindowHandle -ne 0 -and $_.SessionId -eq (Get-Process -Id $PID).SessionId } | Select -First 1
      if ($p) { [W]::SetForegroundWindow($p.MainWindowHandle) | Out-Null; $r += "focused $($p.Id)" } else { $r += 'no Claude window in this session' }
    }
    default { $r += "unknown action $($c.a)" }
  }
  ($r + 'done') | Set-Content -Encoding utf8 $out
} catch { ("error: " + $_.Exception.Message, 'done') | Set-Content -Encoding utf8 $out }
