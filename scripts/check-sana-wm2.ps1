# Check if inference_sana_wm.py is on main branch now
$urls = @(
    "https://raw.githubusercontent.com/NVlabs/Sana/main/inference_video_scripts/inference_sana_wm.py",
    "https://raw.githubusercontent.com/NVlabs/Sana/main/sana/conf.py"
)

foreach ($url in $urls) {
    try {
        $resp = Invoke-WebRequest -Uri $url -Method Head -TimeoutSec 10 -UseBasicParsing
        Write-Host "EXISTS: $url (Status: $($resp.StatusCode))"
    } catch {
        Write-Host "NOT FOUND: $url"
    }
}

# Try to fetch the inference script content (first 30 lines)
try {
    $content = Invoke-RestMethod -Uri "https://api.github.com/repos/NVlabs/Sana/contents/inference_video_scripts/inference_sana_wm.py" -TimeoutSec 15
    Write-Host ""
    Write-Host "inference_sana_wm.py found on main branch!"
    Write-Host "Size: $($content.size) bytes"
    Write-Host "SHA: $($content.sha)"
    Write-Host "Download URL: $($content.download_url)"
} catch {
    Write-Host "inference_sana_wm.py NOT on main branch yet"
    Write-Host "Error: $($_.Exception.Message)"
}

# Check the WM docs page
try {
    $wmPage = Invoke-WebRequest -Uri "https://raw.githubusercontent.com/NVlabs/Sana/main/docs/sana/wm/index.html" -TimeoutSec 10 -UseBasicParsing
    Write-Host ""
    Write-Host "WM docs page exists on main branch ($($wmPage.Content.Length) bytes)"
} catch {
    Write-Host "WM docs page not on main"
}
