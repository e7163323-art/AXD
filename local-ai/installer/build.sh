#!/usr/bin/env bash
# בונה את Gaon-Setup.exe (אפשר להריץ גם מלינוקס – קומפילציה צולבת של Go לווינדוס).
set -euo pipefail
cd "$(dirname "$0")"
ROOT=..
OUT=${OUT:-$ROOT/build/out}
PAY=setup/payload
rm -rf "$PAY" && mkdir -p "$PAY/app" "$PAY/assets" "$OUT"

python3 "$ROOT/build/make_icon.py"
cp "$ROOT"/app/*.py "$PAY/app/"
cp "$ROOT/assets/gaon.ico" "$PAY/assets/"
cp "$ROOT/download_model.bat" "$ROOT/README.md" "$PAY/"
# PowerShell 5.1 צריך BOM כדי לקרוא עברית נכון
printf '\xEF\xBB\xBF' > "$PAY/install.ps1"
sed '1s/^\xEF\xBB\xBF//' install.ps1 >> "$PAY/install.ps1"

export GOOS=windows GOARCH=amd64 CGO_ENABLED=0
RSRC="go run github.com/akavel/rsrc@v0.10.2"
GOOS= GOARCH= $RSRC -arch amd64 -manifest app.manifest -ico "$ROOT/assets/gaon.ico" -o launcher/rsrc_windows_amd64.syso
GOOS= GOARCH= $RSRC -arch amd64 -manifest app.manifest -ico "$ROOT/assets/gaon.ico" -o setup/rsrc_windows_amd64.syso
go build -trimpath -ldflags "-H windowsgui" -o "$PAY/Gaon.exe" ./launcher
go build -trimpath -ldflags "-H windowsgui" -o "$OUT/Gaon-Setup.exe" ./setup
rm -f launcher/*.syso setup/*.syso
ls -la "$OUT/Gaon-Setup.exe"
