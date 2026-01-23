# gen_mac.ps1
# 该脚本用于从 server.py 生成适用于 Mac 的 server.mac.py

$inputFile = "server.py"
$outputFile = "server.mac.py"

if (-Not (Test-Path $inputFile)) {
    Write-Host "错误: 找不到 $inputFile" -ForegroundColor Red
    exit 1
}

Write-Host "正在读取 $inputFile..."
$content = Get-Content -Path $inputFile -Raw -Encoding UTF8

# 1. 移除 printscreen 键的映射
# 匹配 'prtsc': Key.print_screen, 以及后面可能存在的空格/换行
Write-Host "正在修改 SPECIAL_KEYS (移除 printscreen)..."
$content = $content -replace "'prtsc': Key.print_screen,\s*", ""

# 2. 修改滚动方向 (将 data['dy'] 改为 -data['dy'])
Write-Host "正在修改 handle_scroll (反转滚动方向)..."
$content = $content -replace "mouse\.scroll\(0, data\['dy'\]\)", "mouse.scroll(0, -data['dy'])"

# 保存到新文件
$content | Set-Content -Path $outputFile -Encoding UTF8
Write-Host "成功生成: $outputFile" -ForegroundColor Green
