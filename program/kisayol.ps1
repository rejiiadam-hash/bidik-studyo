param([string]$Kok)
# Masaustune "Bidik Studyo" kisayolu olusturur (her calistirmada gunceller)
$masaustu = [Environment]::GetFolderPath('Desktop')
$wsh = New-Object -ComObject WScript.Shell
$k = $wsh.CreateShortcut((Join-Path $masaustu 'Bıdık Stüdyo.lnk'))
$k.TargetPath = (Join-Path $Kok '.venv\Scripts\pythonw.exe')
$k.Arguments = '"' + (Join-Path $Kok 'program\uygulama.py') + '"'
$k.WorkingDirectory = $Kok
$k.IconLocation = (Join-Path $Kok 'program\bidik.ico') + ',0'
$k.Description = 'Bıdık Stüdyo - Shorts üretim uygulaması'
$k.Save()
