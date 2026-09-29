//go:build windows

// Gaon.exe – מפעיל את התוכנה מתוך פייתון המובנה בתיקיית ההתקנה.
package main

import (
	"os"
	"os/exec"
	"path/filepath"

	"gaon/installer/winapi"
)

func main() {
	exe, err := os.Executable()
	if err != nil {
		winapi.Error("גאון", err.Error())
		return
	}
	base := filepath.Dir(exe)
	pyw := filepath.Join(base, "runtime", "python", "pythonw.exe")
	script := filepath.Join(base, "app", "main.py")
	if _, err := os.Stat(pyw); err != nil {
		winapi.Error("גאון", "התוכנה לא הותקנה עד הסוף.\nהפעל שוב את Gaon-Setup.exe.")
		return
	}
	cmd := exec.Command(pyw, script)
	cmd.Dir = base
	if err := cmd.Start(); err != nil {
		winapi.Error("גאון", "לא הצלחתי להפעיל את התוכנה:\n"+err.Error())
	}
}
