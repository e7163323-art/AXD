# עדכון גאון: מוצא לבד את תיקיית ההתקנה (לפי הקיצורים) ומחליף את קבצי התוכנה.
Add-Type -AssemblyName System.Windows.Forms
$src = Join-Path $PSScriptRoot 'app'
$targets = @()
$shell = New-Object -ComObject WScript.Shell
foreach ($folder in @([Environment]::GetFolderPath('Desktop'), [Environment]::GetFolderPath('Programs'),
                      [Environment]::GetFolderPath('CommonDesktopDirectory'))) {
    Get-ChildItem $folder -Filter '*.lnk' -ErrorAction SilentlyContinue | Where-Object { $_.Name -like '*גאון*' } | ForEach-Object {
        $l = $shell.CreateShortcut($_.FullName)
        if ($l.WorkingDirectory) { $targets += $l.WorkingDirectory }
        if ($l.Arguments -match '"?(.+?)\\app\\main\.py"?') { $targets += $Matches[1] }
    }
}
$mem = Join-Path $env:LOCALAPPDATA 'Gaon\install_dir.txt'
if (Test-Path $mem) { $targets += (Get-Content $mem -Raw -Encoding UTF8).Trim() }
$done = @()
foreach ($t in ($targets | Where-Object { $_ } | Select-Object -Unique)) {
    if (Test-Path (Join-Path $t 'app\main.py')) {
        Copy-Item (Join-Path $src '*') (Join-Path $t 'app') -Force
        $done += $t
    }
}
if ($done.Count -gt 0) {
    $msg = "✔ גאון עודכן בתיקיות:`n`n" + ($done -join "`n") + "`n`nסגור את גאון (אם פתוח) ופתח אותו מחדש."
    $icon = [System.Windows.Forms.MessageBoxIcon]::Information
} else {
    $msg = "לא מצאתי את תיקיית גאון.`nחלץ את התיקייה app ידנית לתוך תיקיית גאון."
    $icon = [System.Windows.Forms.MessageBoxIcon]::Warning
}
[System.Windows.Forms.MessageBox]::Show($msg, 'עדכון גאון', [System.Windows.Forms.MessageBoxButtons]::OK, $icon,
    [System.Windows.Forms.MessageBoxDefaultButton]::Button1,
    ([System.Windows.Forms.MessageBoxOptions]::RtlReading -bor [System.Windows.Forms.MessageBoxOptions]::RightAlign)) | Out-Null
