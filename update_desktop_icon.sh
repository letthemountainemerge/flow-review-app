#!/bin/bash
set -e

echo "正在生成图标..."

# 1. 裁剪并缩放
python3 << 'PYEOF'
from PIL import Image

img = Image.open('/Users/yangpuyu/Downloads/image_149497115115816.png').convert('RGBA')
w, h = img.size

def is_content(pixel):
    r, g, b, a = pixel
    if r > 220 and g > 220 and b > 220:
        return False
    if a < 240:
        return False
    return True

left, right, top, bottom = w, 0, h, 0
for y in range(h):
    for x in range(w):
        if is_content(img.getpixel((x, y))):
            if x < left: left = x
            if x > right: right = x
            if y < top: top = y
            if y > bottom: bottom = y

cropped = img.crop((left, top, right+1, bottom+1))
icon = cropped.resize((1024, 1024), Image.LANCZOS)
icon.save('/Users/yangpuyu/Downloads/icon_1024.png')
print("已生成 1024x1024 图标")
PYEOF

# 2. 生成 icns
mkdir -p /tmp/iconset.iconset
sips -z 16 16     /Users/yangpuyu/Downloads/icon_1024.png --out /tmp/iconset.iconset/icon_16x16.png
sips -z 32 32     /Users/yangpuyu/Downloads/icon_1024.png --out /tmp/iconset.iconset/icon_16x16@2x.png
sips -z 32 32     /Users/yangpuyu/Downloads/icon_1024.png --out /tmp/iconset.iconset/icon_32x32.png
sips -z 64 64     /Users/yangpuyu/Downloads/icon_1024.png --out /tmp/iconset.iconset/icon_32x32@2x.png
sips -z 128 128   /Users/yangpuyu/Downloads/icon_1024.png --out /tmp/iconset.iconset/icon_128x128.png
sips -z 256 256   /Users/yangpuyu/Downloads/icon_1024.png --out /tmp/iconset.iconset/icon_128x128@2x.png
sips -z 256 256   /Users/yangpuyu/Downloads/icon_1024.png --out /tmp/iconset.iconset/icon_256x256.png
sips -z 512 512   /Users/yangpuyu/Downloads/icon_1024.png --out /tmp/iconset.iconset/icon_256x256@2x.png
sips -z 512 512   /Users/yangpuyu/Downloads/icon_1024.png --out /tmp/iconset.iconset/icon_512x512.png
sips -z 1024 1024 /Users/yangpuyu/Downloads/icon_1024.png --out /tmp/iconset.iconset/icon_512x512@2x.png
iconutil -c icns /tmp/iconset.iconset -o /Users/yangpuyu/Downloads/AppIcon.icns
rm -rf /tmp/iconset.iconset

# 3. 应用到 app
APP="$HOME/Desktop/流程评审系统.app"
cp /Users/yangpuyu/Downloads/AppIcon.icns "$APP/Contents/Resources/AppIcon.icns"

# 刷新图标缓存
touch "$APP"
rm -f "$HOME/Desktop/Icon?"

# 重启 Finder 以刷新图标（可选）
# killall Finder

echo "图标已更新，如果桌面未立即刷新，可以右键点击 app 选择「显示简介」查看新图标。"
