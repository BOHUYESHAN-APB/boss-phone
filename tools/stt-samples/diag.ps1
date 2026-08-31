param([string]$WavPath)
$ErrorActionPreference = 'Continue'
try {
    Add-Type -AssemblyName System.Speech
    [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
    $rec = New-Object System.Speech.Recognition.SpeechRecognitionEngine([System.Globalization.CultureInfo]::GetCultureInfo('zh-CN'))
    $rec.LoadGrammar((New-Object System.Speech.Recognition.DictationGrammar))
    $rec.SetInputToWaveFile($WavPath)
    $r = $rec.Recognize([TimeSpan]::FromSeconds(10))
    if ($r) { Write-Host ('RESULT: ' + $r.Text) } else { Write-Host 'RESULT: null' }
} catch {
    Write-Host ('ERR: ' + $_.Exception.Message)
}
