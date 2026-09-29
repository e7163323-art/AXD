//go:build windows

// Package winapi מכיל עזרים קטנים ל-API של ווינדוס.
package winapi

import (
	"syscall"
	"unsafe"
)

var (
	user32     = syscall.NewLazyDLL("user32.dll")
	messageBox = user32.NewProc("MessageBoxW")
)

const (
	mbIconError  = 0x10
	mbIconInfo   = 0x40
	mbRight      = 0x80000
	mbRTLReading = 0x100000
)

// Error מציג הודעת שגיאה בעברית (מימין לשמאל).
func Error(title, text string) {
	t, _ := syscall.UTF16PtrFromString(title)
	m, _ := syscall.UTF16PtrFromString(text)
	messageBox.Call(0, uintptr(unsafe.Pointer(m)), uintptr(unsafe.Pointer(t)), mbIconError|mbRight|mbRTLReading)
}

// Info מציג הודעת מידע בעברית.
func Info(title, text string) {
	t, _ := syscall.UTF16PtrFromString(title)
	m, _ := syscall.UTF16PtrFromString(text)
	messageBox.Call(0, uintptr(unsafe.Pointer(m)), uintptr(unsafe.Pointer(t)), mbIconInfo|mbRight|mbRTLReading)
}
