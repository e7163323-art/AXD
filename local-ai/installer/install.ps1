# אשף ההתקנה של "גאון – עוזר AI מקומי"
# רץ מתוך Gaon-Setup.exe. מוריד את כל מה שצריך, מתקין, ובסוף הכל עובד בלי אינטרנט.
$ErrorActionPreference = 'Stop'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
Add-Type -AssemblyName System.Windows.Forms, System.Drawing
[System.Windows.Forms.Application]::EnableVisualStyles()

$Here = $PSScriptRoot
$LogFile = Join-Path $Here 'install.log'
function Log($t) {
    $line = "[{0:HH:mm:ss}] {1}" -f (Get-Date), $t
    Add-Content -Path $LogFile -Value $line -Encoding UTF8
    if ($script:logBox) { $script:logBox.AppendText($line + "`r`n") }
}

$PyVer = '3.11.9'
$GhRepos = @('e7163323-art/AXD', 'e7163323-art/2')   # מאגרי GitHub שבהם נשמר עותק של המודל
$Models = @(
    @{ name = 'Qwen2.5-Coder 32B – מומלץ (19.9GB, צריך 24GB זיכרון)'; repo = 'bartowski/Qwen2.5-Coder-32B-Instruct-GGUF'; file = 'Qwen2.5-Coder-32B-Instruct-Q4_K_M.gguf'; gb = 19.9; ram = 24 },
    @{ name = 'Qwen2.5-Coder 32B – איכות מקסימלית (23.3GB, צריך 32GB זיכרון)'; repo = 'bartowski/Qwen2.5-Coder-32B-Instruct-GGUF'; file = 'Qwen2.5-Coder-32B-Instruct-Q5_K_M.gguf'; gb = 23.3; ram = 32 },
    @{ name = 'Qwen2.5-Coder 14B – מהיר (15.7GB, צריך 20GB זיכרון)'; repo = 'bartowski/Qwen2.5-Coder-14B-Instruct-GGUF'; file = 'Qwen2.5-Coder-14B-Instruct-Q8_0.gguf'; gb = 15.7; ram = 20 },
    @{ name = 'Qwen2.5-Coder 14B – הכי חכם שנכנס ל-12GB (7.3GB, איטי יותר)'; repo = 'bartowski/Qwen2.5-Coder-14B-Instruct-GGUF'; file = 'Qwen2.5-Coder-14B-Instruct-Q3_K_M.gguf'; gb = 7.3; ram = 12 },
    @{ name = 'Qwen2.5-Coder 7B – (8.1GB, צריך 16GB זיכרון)'; repo = 'bartowski/Qwen2.5-Coder-7B-Instruct-GGUF'; file = 'Qwen2.5-Coder-7B-Instruct-Q8_0.gguf'; gb = 8.1; ram = 16 },
    @{ name = 'Qwen2.5-Coder 7B – למחשבים עם 8-12GB זיכרון (5.4GB)'; repo = 'bartowski/Qwen2.5-Coder-7B-Instruct-GGUF'; file = 'Qwen2.5-Coder-7B-Instruct-Q5_K_M.gguf'; gb = 5.4; ram = 8 }
)
$RamGB = [math]::Round((Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory / 1GB)

if (Test-Path 'F:\') { $DefaultDir = 'F:\2222222222222222222222222\Gaon' }
else { $DefaultDir = Join-Path $env:LOCALAPPDATA 'Programs\Gaon' }

# ------------------------------------------------------------------ חלון
$font = New-Object System.Drawing.Font('Segoe UI', 10)
$form = New-Object System.Windows.Forms.Form
$form.Text = 'התקנת גאון – עוזר AI מקומי'
$form.Size = New-Object System.Drawing.Size(760, 640)
$form.StartPosition = 'CenterScreen'
$form.FormBorderStyle = 'FixedDialog'
$form.MaximizeBox = $false
$form.RightToLeft = 'Yes'
$form.RightToLeftLayout = $true
$form.Font = $font
$form.BackColor = [System.Drawing.Color]::FromArgb(21, 23, 28)
$form.ForeColor = [System.Drawing.Color]::FromArgb(230, 230, 230)
$ico = Join-Path $Here 'assets\gaon.ico'
if (Test-Path $ico) { $form.Icon = New-Object System.Drawing.Icon($ico) }

function Add-Label($text, $x, $y, $w, $h, $size = 10, $bold = $false, $color = $null) {
    $l = New-Object System.Windows.Forms.Label
    $l.Text = $text
    $l.Location = New-Object System.Drawing.Point($x, $y)
    $l.Size = New-Object System.Drawing.Size($w, $h)
    $style = 'Regular'; if ($bold) { $style = 'Bold' }
    $l.Font = New-Object System.Drawing.Font('Segoe UI', $size, [System.Drawing.FontStyle]$style)
    if ($color) { $l.ForeColor = $color }
    $form.Controls.Add($l)
    return $l
}
$blue = [System.Drawing.Color]::FromArgb(91, 155, 255)
$muted = [System.Drawing.Color]::FromArgb(150, 158, 172)

Add-Label '🧠 גאון – עוזר AI מקומי בעברית' 20 15 700 40 18 $true $blue | Out-Null
Add-Label "כותב קוד, בונה תוכנות EXE ותוספים לכרום, ושולט במחשב – רק באישור שלך.`nאחרי ההתקנה הכל עובד 100% בלי אינטרנט." 20 60 700 45 10 $false $muted | Out-Null

Add-Label 'תיקיית התקנה:' 20 120 700 22 10 $true | Out-Null
$dirBox = New-Object System.Windows.Forms.TextBox
$dirBox.Location = New-Object System.Drawing.Point(20, 145)
$dirBox.Size = New-Object System.Drawing.Size(580, 28)
$dirBox.Text = $DefaultDir
$dirBox.RightToLeft = 'No'
$form.Controls.Add($dirBox)
$browse = New-Object System.Windows.Forms.Button
$browse.Text = 'עיון…'
$browse.Location = New-Object System.Drawing.Point(610, 143)
$browse.Size = New-Object System.Drawing.Size(110, 30)
$browse.FlatStyle = 'Flat'
$browse.Add_Click({
    $d = New-Object System.Windows.Forms.FolderBrowserDialog
    $d.Description = 'בחר איפה להתקין את גאון'
    if ($d.ShowDialog() -eq 'OK') { $dirBox.Text = Join-Path $d.SelectedPath 'Gaon' }
})
$form.Controls.Add($browse)

Add-Label "מודל AI להורדה (זיכרון במחשב שלך: ${RamGB}GB):" 20 190 700 22 10 $true | Out-Null
$modelBox = New-Object System.Windows.Forms.ComboBox
$modelBox.DropDownStyle = 'DropDownList'
$modelBox.Location = New-Object System.Drawing.Point(20, 215)
$modelBox.Size = New-Object System.Drawing.Size(700, 30)
foreach ($m in $Models) { [void]$modelBox.Items.Add($m.name) }
[void]$modelBox.Items.Add('לא עכשיו – אבחר מתוך התוכנה')
$rec = $Models.Count - 1
for ($i = 0; $i -lt $Models.Count; $i++) { if ($RamGB -ge $Models[$i].ram -and $i -ne 1) { $rec = $i; break } }
$modelBox.SelectedIndex = $rec
$form.Controls.Add($modelBox)

$desk = New-Object System.Windows.Forms.CheckBox
$desk.Text = 'צור קיצור דרך בשולחן העבודה'
$desk.Checked = $true
$desk.Location = New-Object System.Drawing.Point(20, 255)
$desk.Size = New-Object System.Drawing.Size(400, 26)
$form.Controls.Add($desk)

$status = Add-Label 'מוכן להתקנה.' 20 295 700 24 10 $true
$progress = New-Object System.Windows.Forms.ProgressBar
$progress.Location = New-Object System.Drawing.Point(20, 322)
$progress.Size = New-Object System.Drawing.Size(700, 24)
$progress.RightToLeftLayout = $true
$form.Controls.Add($progress)

$script:logBox = New-Object System.Windows.Forms.TextBox
$logBox.Multiline = $true
$logBox.ScrollBars = 'Vertical'
$logBox.ReadOnly = $true
$logBox.Location = New-Object System.Drawing.Point(20, 356)
$logBox.Size = New-Object System.Drawing.Size(700, 170)
$logBox.BackColor = [System.Drawing.Color]::FromArgb(29, 32, 39)
$logBox.ForeColor = [System.Drawing.Color]::FromArgb(200, 210, 220)
$logBox.Font = New-Object System.Drawing.Font('Consolas', 9)
$form.Controls.Add($logBox)

$go = New-Object System.Windows.Forms.Button
$go.Text = '✔ התקן'
$go.Location = New-Object System.Drawing.Point(20, 540)
$go.Size = New-Object System.Drawing.Size(180, 42)
$go.BackColor = [System.Drawing.Color]::FromArgb(43, 108, 246)
$go.ForeColor = [System.Drawing.Color]::White
$go.FlatStyle = 'Flat'
$go.Font = New-Object System.Drawing.Font('Segoe UI', 11, [System.Drawing.FontStyle]::Bold)
$form.Controls.Add($go)

$cancel = New-Object System.Windows.Forms.Button
$cancel.Text = 'ביטול'
$cancel.Location = New-Object System.Drawing.Point(210, 540)
$cancel.Size = New-Object System.Drawing.Size(120, 42)
$cancel.FlatStyle = 'Flat'
$form.Controls.Add($cancel)
$script:cancelled = $false
$cancel.Add_Click({ if ($script:busy) { $script:cancelled = $true } else { $form.Close() } })

# ------------------------------------------------------------------ עזרים
function Pump { [System.Windows.Forms.Application]::DoEvents() }
function Set-Status($t) { $status.Text = $t; Log $t; Pump }
function Check-Cancel { if ($script:cancelled) { throw 'ההתקנה בוטלה על ידי המשתמש.' } }

function Wait-Proc($p, $label, $destFile = $null, $expected = 0) {
    $null = $p.Handle
    while (-not $p.HasExited) {
        if ($script:cancelled) { try { $p.Kill() } catch {}; throw 'ההתקנה בוטלה על ידי המשתמש.' }
        if ($destFile -and $expected -gt 0 -and (Test-Path $destFile)) {
            $size = (Get-Item $destFile).Length
            $pct = [math]::Min(100, [int](100 * $size / $expected))
            $progress.Style = 'Continuous'
            $progress.Value = $pct
            $status.Text = '{0} – {1:N2}GB מתוך {2:N2}GB ({3}%)' -f $label, ($size / 1GB), ($expected / 1GB), $pct
        } else {
            $progress.Style = 'Marquee'
        }
        Pump
        Start-Sleep -Milliseconds 200
    }
    $progress.Style = 'Continuous'
    return $p.ExitCode
}

function Download-DotNet($url, $part, $label, $expectedBytes) {
    Log "מנסה דרך הורדה חלופית…"
    $wc = New-Object System.Net.WebClient
    $wc.Headers.Add('User-Agent', 'Gaon-Setup/1.0')
    if (Test-Path $part) { Remove-Item $part -Force }
    $task = $wc.DownloadFileTaskAsync($url, $part)
    while (-not $task.IsCompleted) {
        if ($script:cancelled) { $wc.CancelAsync(); throw 'ההתקנה בוטלה על ידי המשתמש.' }
        if ($expectedBytes -gt 0 -and (Test-Path $part)) {
            $size = (Get-Item $part).Length
            $pct = [math]::Min(100, [int](100 * $size / $expectedBytes))
            $progress.Style = 'Continuous'
            $progress.Value = $pct
            $status.Text = '{0} – {1:N2}GB מתוך {2:N2}GB ({3}%)' -f $label, ($size / 1GB), ($expectedBytes / 1GB), $pct
        } else { $progress.Style = 'Marquee' }
        Pump
        Start-Sleep -Milliseconds 200
    }
    $progress.Style = 'Continuous'
    if ($task.IsFaulted) {
        $e = $task.Exception.InnerException
        while ($e.InnerException) { $e = $e.InnerException }
        throw "ההורדה נכשלה: $label`n$($e.Message)"
    }
}

function Download($url, $dest, $label, $expectedBytes = 0) {
    Set-Status "מוריד: $label"
    $part = "$dest.part"
    # --ssl-no-revoke: מונע את שגיאה 35 כשבדיקת אישורי האבטחה נחסמת (אנטי-וירוס/רשת)
    $cargs = @('-L', '--fail', '--ssl-no-revoke', '-C', '-', '--retry', '10', '--retry-delay', '3', '-s', '-S',
              '-A', 'Gaon-Setup/1.0', '-o', "`"$part`"", "`"$url`"")
    $code = -1
    if (Get-Command curl.exe -ErrorAction SilentlyContinue) {
        for ($try = 1; $try -le 3; $try++) {
            $p = Start-Process -FilePath 'curl.exe' -ArgumentList $cargs -PassThru -WindowStyle Hidden
            $code = Wait-Proc $p $label $part $expectedBytes
            if ($code -eq 0) { break }
            Log "curl החזיר קוד $code – מנסה שוב ($try)"
            Check-Cancel
            Start-Sleep -Seconds 2
        }
    }
    if ($code -ne 0) { Download-DotNet $url $part $label $expectedBytes }
    Move-Item -Force $part $dest
}

function Run($exe, $argList, $label) {
    Set-Status $label
    $out = Join-Path $Here ("proc_{0}.log" -f (Get-Random))
    $p = Start-Process -FilePath $exe -ArgumentList $argList -PassThru -WindowStyle Hidden `
        -RedirectStandardOutput $out -RedirectStandardError "$out.err"
    $code = Wait-Proc $p $label
    if (Test-Path $out) { Get-Content $out -Tail 5 -Encoding UTF8 | ForEach-Object { Log $_ } }
    if (Test-Path "$out.err") { Get-Content "$out.err" -Tail 5 -Encoding UTF8 | ForEach-Object { Log $_ } }
    return $code
}

# ------------------------------------------------------------------ התקנה
function Install {
    $dir = $dirBox.Text.Trim()
    $dl = Join-Path $dir '_downloads'
    New-Item -ItemType Directory -Force $dir, $dl, "$dir\models", "$dir\engine", "$dir\runtime" | Out-Null
    $progress.Value = 0

    # 1. קבצי התוכנה
    Set-Status 'מעתיק את קבצי התוכנה…'
    foreach ($item in 'app', 'assets', 'Gaon.exe', 'download_model.bat', 'README.md') {
        $src = Join-Path $Here $item
        if (Test-Path $src -PathType Container) {
            New-Item -ItemType Directory -Force "$dir\$item" | Out-Null
            Copy-Item "$src\*" "$dir\$item" -Recurse -Force
        } elseif (Test-Path $src) { Copy-Item $src $dir -Force }
    }
    New-Item -ItemType Directory -Force "$dir\פרויקטים" | Out-Null

    # 2. פייתון מובנה (לתוכנה ולבניית EXE בלי אינטרנט)
    $py = Join-Path $dir 'runtime\python'
    if (-not (Test-Path "$py\python.exe")) {
        $pyExe = Join-Path $dl "python-$PyVer-amd64.exe"
        if (-not (Test-Path $pyExe)) { Download "https://www.python.org/ftp/python/$PyVer/python-$PyVer-amd64.exe" $pyExe 'פייתון' 26MB }
        Run $pyExe @('/quiet', 'InstallAllUsers=0', "`"TargetDir=$py`"", 'Include_launcher=0', 'InstallLauncherAllUsers=0',
                     'PrependPath=0', 'Shortcuts=0', 'Include_test=0', 'Include_doc=0', 'AssociateFiles=0',
                     'Include_tcltk=1', 'Include_pip=1') 'מתקין פייתון…' | Out-Null
        if (-not (Test-Path "$py\python.exe")) {
            Log 'התקנת פייתון הרגילה לא הצליחה – עובר לחבילה ניידת.'
            $nupkg = Join-Path $dl "python.$PyVer.zip"
            Download "https://www.nuget.org/api/v2/package/python/$PyVer" $nupkg 'פייתון (נייד)' 15MB
            $tmp = Join-Path $dl 'py_nuget'
            Expand-Archive $nupkg $tmp -Force
            Copy-Item "$tmp\tools" $py -Recurse -Force
            Run "$py\python.exe" @('-m', 'ensurepip', '--upgrade') 'מכין את pip…' | Out-Null
        }
    }
    if (-not (Test-Path "$py\python.exe")) { throw 'לא הצלחתי להתקין פייתון.' }
    Check-Cancel
    Run "$py\python.exe" @('-m', 'pip', 'install', '--upgrade', '--no-warn-script-location', 'pip') 'מעדכן את pip…' | Out-Null
    $code = Run "$py\python.exe" @('-m', 'pip', 'install', '--no-warn-script-location', 'PySide6', 'pyinstaller',
                                   'pillow', 'requests', 'customtkinter', 'pygame') 'מתקין רכיבי ממשק ובנייה (כ-300MB, כמה דקות)…'
    if ($code -ne 0) { throw 'התקנת הרכיבים נכשלה. בדוק חיבור לאינטרנט והפעל שוב את ההתקנה.' }
    $progress.Value = 100
    Check-Cancel

    # 3. מנוע ה-AI (llama.cpp)
    if (-not (Test-Path "$dir\engine\cpu\llama-server.exe")) {
        Set-Status 'בודק את הגרסה האחרונה של מנוע ה-AI…'
        $releases = Invoke-RestMethod -UseBasicParsing 'https://api.github.com/repos/ggml-org/llama.cpp/releases?per_page=15' -Headers @{ 'User-Agent' = 'Gaon-Setup' }
        function Find-Asset($rel, $kind) {
            foreach ($a in $rel.assets) {
                $n = $a.name.ToLower()
                if (-not $n.EndsWith('.zip') -or $n -notmatch 'win' -or $n -match 'arm64' -or $n -match '^cudart') { continue }
                if ($n -notmatch 'x64|x86_64|amd64') { continue }
                switch ($kind) {
                    'cpu'    { if ($n -match 'cpu' -or ($n -match 'avx2' -and $n -notmatch 'cuda|vulkan|hip|sycl|opencl')) { return $a } }
                    'vulkan' { if ($n -match 'vulkan') { return $a } }
                    'cuda'   { if ($n -match 'cuda-1\d') { return $a } }
                }
            }
            return $null
        }
        $rel = $null
        foreach ($r in $releases) { if (Find-Asset $r 'cpu') { $rel = $r; break } }
        if (-not $rel) {
            Log 'קבצים שנמצאו בגרסה האחרונה:'
            foreach ($a in $releases[0].assets) { if ($a.name -match 'win') { Log "  $($a.name)" } }
            throw 'לא נמצא מנוע AI להורדה. צלם את רשימת ההודעות ושלח לי.'
        }
        Log "llama.cpp $($rel.tag_name)"
        $want = [ordered]@{ cpu = 'cpu'; vulkan = 'vulkan' }
        $nvidia = Test-Path "$env:SystemRoot\System32\nvcuda.dll"
        if ($nvidia) { $want['cuda'] = 'cuda' }
        foreach ($k in $want.Keys) {
            $asset = Find-Asset $rel $want[$k]
            if (-not $asset) { Log "לא נמצא מנוע $k – ממשיך בלעדיו"; continue }
            Log "מנוע $($k): $($asset.name)"
            $zip = Join-Path $dl $asset.name
            if (-not (Test-Path $zip)) { Download $asset.browser_download_url $zip "מנוע AI ($k)" $asset.size }
            $tmp = Join-Path $dl "eng_$k"
            Expand-Archive $zip $tmp -Force
            $server = Get-ChildItem $tmp -Recurse -Filter llama-server.exe | Select-Object -First 1
            if (-not $server) { Log "אין llama-server.exe בתוך $($asset.name)"; if ($k -eq 'cpu') { throw 'קובץ המנוע לא תקין.' }; continue }
            New-Item -ItemType Directory -Force "$dir\engine\$k" | Out-Null
            Copy-Item "$($server.DirectoryName)\*" "$dir\engine\$k" -Recurse -Force
            if ($k -eq 'cuda') {
                $cv = [regex]::Match($asset.name, 'cuda-(\d+\.\d+)').Groups[1].Value
                $rt = $rel.assets | Where-Object { $_.name -match "^cudart-.*win-cuda-$([regex]::Escape($cv))-x64\.zip$" } | Select-Object -First 1
                if ($rt) {
                    $rz = Join-Path $dl $rt.name
                    if (-not (Test-Path $rz)) { Download $rt.browser_download_url $rz 'ספריות CUDA' $rt.size }
                    Expand-Archive $rz "$dl\cudart" -Force
                    Get-ChildItem "$dl\cudart" -Recurse -Filter *.dll | Copy-Item -Destination "$dir\engine\cuda" -Force
                } else { Remove-Item "$dir\engine\cuda" -Recurse -Force }
            }
            Check-Cancel
        }
    }

    # 4. קיצורי דרך
    Set-Status 'יוצר קיצורי דרך…'
    $shell = New-Object -ComObject WScript.Shell
    $targets = @([Environment]::GetFolderPath('Programs'))
    if ($desk.Checked) { $targets += [Environment]::GetFolderPath('Desktop') }
    foreach ($t in $targets) {
        $lnk = $shell.CreateShortcut((Join-Path $t 'גאון - עוזר AI מקומי.lnk'))
        # קיצור ישיר לפייתון – עובד גם אם אנטי-וירוס חוסם את Gaon.exe
        $lnk.TargetPath = "$dir\runtime\python\pythonw.exe"
        $lnk.Arguments = "`"$dir\app\main.py`""
        $lnk.WorkingDirectory = $dir
        $lnk.IconLocation = "$dir\assets\gaon.ico"
        $lnk.Description = 'עוזר AI מקומי בעברית'
        $lnk.Save()
    }

    # 5. המודל (15-23GB)
    $mi = $modelBox.SelectedIndex
    if ($mi -lt $Models.Count) {
        $m = $Models[$mi]
        $dest = Join-Path "$dir\models" $m.file
        if (-not (Test-Path $dest)) {
            $free = (Get-PSDrive ($dir.Substring(0, 1))).Free / 1GB
            try { $fsType = (Get-Volume -DriveLetter $dir.Substring(0, 1)).FileSystem } catch { $fsType = '' }
            if ($fsType -eq 'FAT32') { throw "הכונן $($dir.Substring(0, 1)): מפורמט ב-FAT32 ולא יכול לשמור קובץ גדול מ-4GB.`nבחר תיקיית התקנה בכונן C (למשל C:\Gaon) והפעל שוב." }
            if ($free -lt $m.gb + 1) { throw ("אין מספיק מקום בכונן: צריך {0:N0}GB ויש {1:N0}GB." -f ($m.gb + 1), $free) }
            $base = $m.file.ToLower() -replace '\.gguf$', ''
            $msRepo = ($m.repo -replace '^bartowski/', 'Qwen/')
            $urls = @(
                "https://huggingface.co/$($m.repo)/resolve/main/$($m.file)?download=true",
                "https://hf-mirror.com/$($m.repo)/resolve/main/$($m.file)?download=true",
                "https://modelscope.cn/models/$msRepo/resolve/master/$base.gguf"
            )
            $ok = $false; $lastErr = ''
            # מקור ראשון: עותק ב-GitHub (מחולק לחלקים) – עובד גם באינטרנט מסונן
            try {
                Set-Status 'בודק אם יש עותק של המודל ב-GitHub…'
                $parts = @()
                foreach ($gr in $GhRepos) {
                    try {
                        $ghRel = Invoke-RestMethod -UseBasicParsing "https://api.github.com/repos/$gr/releases/tags/gaon-models" -Headers @{ 'User-Agent' = 'Gaon-Setup' }
                        $parts = @($ghRel.assets | Where-Object { $_.name -like "$($m.file).part*" } | Sort-Object name)
                        if ($parts.Count -gt 0) { Log "נמצא עותק של המודל ב-$gr"; break }
                    } catch { Log "אין עותק ב-$gr" }
                }
                if ($parts.Count -gt 0) {
                    $i = 0
                    foreach ($pa in $parts) {
                        $i++
                        $pf = Join-Path $dl $pa.name
                        if (-not (Test-Path $pf) -or (Get-Item $pf).Length -ne $pa.size) {
                            Download $pa.browser_download_url $pf "המודל – חלק $i מתוך $($parts.Count)" $pa.size
                        }
                    }
                    Set-Status 'מחבר את חלקי המודל…'
                    $out = [IO.File]::Create("$dest.part")
                    foreach ($pa in $parts) {
                        $in = [IO.File]::OpenRead((Join-Path $dl $pa.name))
                        $in.CopyTo($out, 4MB)
                        $in.Close()
                        Pump
                    }
                    $out.Close()
                    Move-Item -Force "$dest.part" $dest
                    $ok = $true
                } else { Log 'אין עותק של המודל ב-GitHub.' }
            } catch {
                Log "העותק ב-GitHub לא זמין: $($_.Exception.Message)"
                Check-Cancel
            }
            foreach ($u in $urls) {
                if ($ok) { break }
                try {
                    Log "מנסה להוריד מ: $(([uri]$u).Host)"
                    Download $u $dest "המודל $($m.file)" ([int64]($m.gb * 1e9))
                    $ok = $true; break
                } catch {
                    $lastErr = $_.Exception.Message
                    Log "לא הצליח: $lastErr"
                    Check-Cancel
                }
            }
            if (-not $ok) {
                throw ("לא הצלחתי להוריד את המודל מאף אתר.`n$lastErr`n`n" +
                       "כנראה שסינון האינטרנט חוסם את האתרים huggingface.co ו-hf-mirror.com.`n" +
                       "אפשר לבקש מספק הסינון לפתוח אותם, או להוריד את הקובץ במחשב אחר ולשים אותו בתיקייה models.")
            }
        }
        New-Item -ItemType Directory -Force "$dir\data" | Out-Null
        $settings = @{ model_file = $dest } | ConvertTo-Json
        [IO.File]::WriteAllText("$dir\data\settings.json", $settings, (New-Object Text.UTF8Encoding($false)))
    }

    Remove-Item $dl -Recurse -Force -ErrorAction SilentlyContinue
    $progress.Value = 100
    Set-Status '✔ ההתקנה הושלמה! מעכשיו הכל עובד בלי אינטרנט.'
    return $dir
}

$script:busy = $false
$go.Add_Click({
    if ($script:done) {
        Start-Process -FilePath "$($script:done)\runtime\python\pythonw.exe" -ArgumentList "`"$($script:done)\app\main.py`"" -WorkingDirectory $script:done
        $form.Close(); return
    }
    $script:busy = $true
    $go.Enabled = $false; $dirBox.Enabled = $false; $browse.Enabled = $false; $modelBox.Enabled = $false
    try {
        $script:done = Install
        $go.Text = '▶ הפעל את גאון'
        $go.Enabled = $true
        $cancel.Text = 'סגור'
    } catch {
        Log "שגיאה: $($_.Exception.Message)"
        Set-Status 'ההתקנה נעצרה.'
        [System.Windows.Forms.MessageBox]::Show($_.Exception.Message + "`n`nאפשר להפעיל שוב את ההתקנה – היא תמשיך מאיפה שעצרה.",
            'התקנת גאון', [System.Windows.Forms.MessageBoxButtons]::OK, [System.Windows.Forms.MessageBoxIcon]::Error,
            [System.Windows.Forms.MessageBoxDefaultButton]::Button1,
            ([System.Windows.Forms.MessageBoxOptions]::RtlReading -bor [System.Windows.Forms.MessageBoxOptions]::RightAlign)) | Out-Null
        $go.Enabled = $true; $dirBox.Enabled = $true; $browse.Enabled = $true; $modelBox.Enabled = $true
        $script:cancelled = $false
    }
    $script:busy = $false
})
$form.Add_FormClosing({ param($s, $e) if ($script:busy) { $script:cancelled = $true; $e.Cancel = $true } })

Log "התחלת אשף ההתקנה. זיכרון: ${RamGB}GB"
$form.WindowState = 'Normal'
$form.ShowInTaskbar = $true
$form.Add_Shown({ $form.TopMost = $true; $form.Activate(); $form.TopMost = $false })
[void]$form.ShowDialog()
