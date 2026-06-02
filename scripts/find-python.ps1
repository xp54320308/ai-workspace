# Find all Python installations
$paths = @(
    "C:\Users\qw\AppData\Roaming\uv\python\cpython-3.11.15-windows-x86_64-none\python.exe",
    "C:\Users\qw\AppData\Local\Programs\Python\Python310\python.exe",
    "C:\Users\qw\AppData\Local\Programs\Python\Python311\python.exe",
    "C:\Python310\python.exe",
    "C:\Python311\python.exe",
    "F:\Comfyui\ComfyUI-aki-v3\python_embeded\python.exe",
    "D:\AI\ComfyUI\ComfyUI_windows_portable\python_embeded\python.exe"
)

foreach ($p in $paths) {
    if (Test-Path $p) {
        $ver = & $p --version 2>&1
        Write-Host "FOUND: $p -> $ver"
    }
}

# Also check for uv
Write-Host ""
Write-Host "--- uv ---"
uv --version 2>$null
