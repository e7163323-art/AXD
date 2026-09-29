//go:build windows

// Gaon-Setup.exe – מחלץ את קבצי ההתקנה ומפעיל את אשף ההתקנה הגרפי בעברית.
package main

import (
	"embed"
	"fmt"
	"io/fs"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"syscall"

	"gaon/installer/winapi"
)

//go:embed all:payload
var payload embed.FS

const title = "התקנת גאון"

func main() {
	winapi.Info(title, "ההתקנה מתחילה.\nלחץ \"אישור\", ובעוד כמה שניות ייפתח חלון ההתקנה.")

	dir := filepath.Join(os.TempDir(), fmt.Sprintf("GaonSetup-%d", os.Getpid()))
	err := fs.WalkDir(payload, "payload", func(p string, d fs.DirEntry, err error) error {
		if err != nil {
			return err
		}
		rel, _ := filepath.Rel("payload", filepath.FromSlash(p))
		target := filepath.Join(dir, rel)
		if d.IsDir() {
			return os.MkdirAll(target, 0o755)
		}
		data, err := payload.ReadFile(p)
		if err != nil {
			return err
		}
		return os.WriteFile(target, data, 0o644)
	})
	if err != nil {
		winapi.Error(title, "שגיאה בחילוץ קבצי ההתקנה:\n"+err.Error())
		return
	}

	errFile := filepath.Join(dir, "powershell_errors.txt")
	out, _ := os.Create(errFile)
	ps := filepath.Join(os.Getenv("SystemRoot"), "System32", "WindowsPowerShell", "v1.0", "powershell.exe")
	if _, err := os.Stat(ps); err != nil {
		ps = "powershell.exe"
	}
	// בלי HideWindow: אחרת ווינדוס מסתיר גם את החלון הראשון של האשף.
	// CREATE_NO_WINDOW מספיק כדי שלא יופיע מסך שחור.
	cmd := exec.Command(ps, "-NoProfile", "-ExecutionPolicy", "Bypass", "-STA",
		"-File", filepath.Join(dir, "install.ps1"))
	cmd.Dir = dir
	cmd.Stdout = out
	cmd.Stderr = out
	cmd.SysProcAttr = &syscall.SysProcAttr{CreationFlags: 0x08000000}
	runErr := cmd.Run()
	out.Close()

	details, _ := os.ReadFile(errFile)
	text := strings.TrimSpace(string(details))
	if len(text) > 1200 {
		text = text[len(text)-1200:]
	}
	if runErr != nil || (text != "" && strings.Contains(text, "Error")) {
		msg := "אשף ההתקנה נעצר עם שגיאה."
		if runErr != nil {
			msg += "\n" + runErr.Error()
		}
		if text != "" {
			msg += "\n\n" + text
		}
		msg += "\n\nצלם את ההודעה הזאת ושלח לי."
		winapi.Error(title, msg)
	}
}
