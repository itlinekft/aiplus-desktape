# desktape look --ocr: Windows built-in OCR (Windows.Media.Ocr) on a full-screen capture, run in the
# interactive session by a one-off task. Writes %USERPROFILE%\desktape\ocr-out.json, then ocr-done.txt. ASCII only.
$ErrorActionPreference = 'Stop'
$d = Join-Path $env:USERPROFILE 'desktape'
$out = Join-Path $d 'ocr-out.json'
try {
  Add-Type -AssemblyName System.Runtime.WindowsRuntime, System.Drawing, System.Windows.Forms
  Add-Type 'using System.Runtime.InteropServices; public static class D { [DllImport("user32.dll")] public static extern bool SetProcessDPIAware(); }'
  [D]::SetProcessDPIAware() | Out-Null
  $asTask = ([System.WindowsRuntimeSystemExtensions].GetMethods() | ? { $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1' })[0]
  function Await($op, [Type]$t) { $task = $asTask.MakeGenericMethod($t).Invoke($null, @($op)); $task.Wait() | Out-Null; $task.Result }
  [void][Windows.Media.Ocr.OcrEngine, Windows.Foundation, ContentType = WindowsRuntime]
  [void][Windows.Graphics.Imaging.BitmapDecoder, Windows.Graphics, ContentType = WindowsRuntime]
  [void][Windows.Storage.StorageFile, Windows.Storage, ContentType = WindowsRuntime]

  $sw = [Diagnostics.Stopwatch]::StartNew()
  $b = [System.Windows.Forms.SystemInformation]::VirtualScreen
  $bmp = New-Object System.Drawing.Bitmap $b.Width, $b.Height
  [System.Drawing.Graphics]::FromImage($bmp).CopyFromScreen($b.Left, $b.Top, 0, 0, $bmp.Size)
  $png = Join-Path $d 'ocr-shot.png'; $bmp.Save($png, [System.Drawing.Imaging.ImageFormat]::Png)
  $tCapture = $sw.ElapsedMilliseconds

  $file = Await ([Windows.Storage.StorageFile]::GetFileFromPathAsync($png)) ([Windows.Storage.StorageFile])
  $stream = Await ($file.OpenAsync([Windows.Storage.FileAccessMode]::Read)) ([Windows.Storage.Streams.IRandomAccessStream])
  $dec = Await ([Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($stream)) ([Windows.Graphics.Imaging.BitmapDecoder])
  $sb = Await ($dec.GetSoftwareBitmapAsync()) ([Windows.Graphics.Imaging.SoftwareBitmap])
  $tDecode = $sw.ElapsedMilliseconds

  $langs = [Windows.Media.Ocr.OcrEngine]::AvailableRecognizerLanguages | % { $_.LanguageTag }
  $runs = @()
  foreach ($tag in $langs) {
    $eng = [Windows.Media.Ocr.OcrEngine]::TryCreateFromLanguage((New-Object Windows.Globalization.Language $tag))
    $t0 = $sw.ElapsedMilliseconds
    $res = Await ($eng.RecognizeAsync($sb)) ([Windows.Media.Ocr.OcrResult])
    $ms = $sw.ElapsedMilliseconds - $t0
    $lines = foreach ($l in $res.Lines) {
      $ws = $l.Words; $x = ($ws | % { $_.BoundingRect.X } | Measure -Min).Minimum; $y = ($ws | % { $_.BoundingRect.Y } | Measure -Min).Minimum
      $r = ($ws | % { $_.BoundingRect.X + $_.BoundingRect.Width } | Measure -Max).Maximum; $btm = ($ws | % { $_.BoundingRect.Y + $_.BoundingRect.Height } | Measure -Max).Maximum
      [ordered]@{ text = $l.Text; x = [int]$x; y = [int]$y; w = [int]($r - $x); h = [int]($btm - $y) }
    }
    $runs += [ordered]@{ lang = $tag; ms = $ms; lineCount = @($lines).Count; lines = @($lines) }
  }
  [ordered]@{ screen = "$($b.Width)x$($b.Height)"; captureMs = $tCapture; decodeMs = $tDecode - $tCapture; languages = $langs; runs = $runs } |
    ConvertTo-Json -Depth 6 | Set-Content -Encoding utf8 $out
} catch { @{ error = $_.Exception.Message } | ConvertTo-Json | Set-Content -Encoding utf8 $out }
'done' | Add-Content -Encoding utf8 (Join-Path $d 'ocr-done.txt')
