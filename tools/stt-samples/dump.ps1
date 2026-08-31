$a = [IO.File]::ReadAllBytes('C:\Users\ETPau\Documents\GITHUB\ai-passport\tools\stt-samples\out\02-bio-bwa.wav')[0..63]
$b = [IO.File]::ReadAllBytes("$env:TEMP\boss-stt-debug.wav")[0..63]
Write-Host ('TTS  : ' + (($a | ForEach-Object { $_.ToString('X2') }) -join ' '))
Write-Host ('hound: ' + (($b | ForEach-Object { $_.ToString('X2') }) -join ' '))
