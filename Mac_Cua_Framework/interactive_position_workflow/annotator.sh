#!/usr/bin/env bash
# Annotator server manager
# Usage:
#   ./annotator.sh start [image.png]   – start server (optionally swap image first)
#   ./annotator.sh stop                – stop server
#   ./annotator.sh restart [image.png] – stop then start
#   ./annotator.sh status              – show if server is running
#   ./annotator.sh use <image.png>     – swap the active image without restarting

set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVER="$DIR/server.py"
HTML="$DIR/annotator.html"
PID_FILE="$DIR/.server.pid"
PORT=8787
LOG="$DIR/.server.log"
DEFAULT_IMAGE="/Users/jiateng5/research/Mac_Cua_Framework/interactive_position_workflow/reference.png"

# ── helpers ──────────────────────────────────────────────────────────────────

open_browser() {
    local url="http://localhost:$PORT"
    open -a Safari "$url" 2>/dev/null \
    || open -a "Google Chrome" "$url" 2>/dev/null \
    || open -a Firefox "$url" 2>/dev/null \
    || open "$url" 2>/dev/null \
    || echo "  (Could not auto-open browser — visit the URL above manually)"
}

is_running() {
    if [[ -f "$PID_FILE" ]]; then
        local pid
        pid=$(cat "$PID_FILE")
        kill -0 "$pid" 2>/dev/null && return 0
    fi
    # Fallback: check port
    lsof -ti :"$PORT" &>/dev/null && return 0
    return 1
}

get_pid() {
    if [[ -f "$PID_FILE" ]]; then cat "$PID_FILE"; fi
    lsof -ti :"$PORT" 2>/dev/null | head -1 || true
}

inject_image() {
    local img="$1"
    # Resolve to absolute path
    [[ "$img" != /* ]] && img="$DIR/$img"

    if [[ ! -f "$img" ]]; then
        echo "ERROR: image not found: $img" >&2; exit 1
    fi

    echo "  Injecting image: $img"
    local b64
    b64=$(base64 < "$img")
    # Detect mime type
    local mime="image/png"
    [[ "$img" == *.jpg || "$img" == *.jpeg ]] && mime="image/jpeg"
    [[ "$img" == *.gif ]] && mime="image/gif"
    [[ "$img" == *.webp ]] && mime="image/webp"

    # Read natural image dimensions
    local w h
    w=$(python3 -c "
import struct, sys
data = open('$img','rb').read(24)
if data[:4] == b'\\x89PNG':
    print(struct.unpack('>I', data[16:20])[0])
else:
    try:
        from PIL import Image
        print(Image.open('$img').size[0])
    except:
        print(0)
")
    h=$(python3 -c "
import struct, sys
data = open('$img','rb').read(24)
if data[:4] == b'\\x89PNG':
    print(struct.unpack('>I', data[20:24])[0])
else:
    try:
        from PIL import Image
        print(Image.open('$img').size[1])
    except:
        print(0)
")

    echo "  Dimensions: ${w}x${h}"

    # Re-generate the HTML from the template, replacing image data and dimensions
    python3 - "$img" "$b64" "$mime" "$w" "$h" "$HTML" << 'PYEOF'
import sys, re, base64, struct

img_path, b64, mime, w, h, html_path = sys.argv[1:]
w, h = int(w), int(h)

with open(html_path, 'r') as f:
    html = f.read()

# Replace base64 image src
html = re.sub(
    r"img\.src\s*=\s*'data:[^']+;base64,[^']*'",
    f"img.src = 'data:{mime};base64,{b64}'",
    html
)

# Replace dimension constants
html = re.sub(r'const IMG_W\s*=\s*\d+', f'const IMG_W = {w}', html)
html = re.sub(r'const IMG_H\s*=\s*\d+', f'const IMG_H = {h}', html)
html = re.sub(r'imgNaturalW\s*=\s*IMG_W,\s*imgNaturalH\s*=\s*IMG_H',
              f'imgNaturalW = IMG_W, imgNaturalH = IMG_H', html)

with open(html_path, 'w') as f:
    f.write(html)

print(f"  HTML updated ({len(html):,} bytes)")
PYEOF
}

do_start() {
    local img="${1:-$DEFAULT_IMAGE}"
    if is_running; then
        echo "Server already running (pid $(get_pid)). Use 'restart' to reload."
        exit 0
    fi
    inject_image "$img"
    echo "Starting server on http://localhost:$PORT ..."
    cd "$DIR"
    nohup python3 "$SERVER" "$PORT" > "$LOG" 2>&1 &
    echo $! > "$PID_FILE"
    sleep 0.6
    if is_running; then
        echo "Server started (pid $(cat "$PID_FILE")). Log: $LOG"
        echo ""
        echo "  ➜  http://localhost:$PORT"
        echo ""
        open_browser
    else
        echo "ERROR: server failed to start. Check $LOG" >&2; exit 1
    fi
}

do_stop() {
    if ! is_running; then
        echo "Server is not running."
        return
    fi
    local pid
    pid=$(get_pid)
    echo "Stopping server (pid $pid)..."
    kill "$pid" 2>/dev/null || true
    lsof -ti :"$PORT" 2>/dev/null | xargs kill -9 2>/dev/null || true
    rm -f "$PID_FILE"
    echo "Stopped."
}

do_status() {
    if is_running; then
        echo "Running  — pid $(get_pid)  — http://localhost:$PORT"
    else
        echo "Stopped."
    fi
}

do_use() {
    local img="${1:-}"
    [[ -z "$img" ]] && { echo "Usage: $0 use <image.png>" >&2; exit 1; }
    inject_image "$img"
    if is_running; then
        echo "Image swapped. Restart the server for changes to take effect:"
        echo "  $0 restart"
    else
        echo "Image swapped (server not running — use '$0 start' to launch)."
    fi
}

# ── dispatch ─────────────────────────────────────────────────────────────────

CMD="${1:-help}"
shift || true

case "$CMD" in
    start)   do_start "${1:-}" ;;
    stop)    do_stop ;;
    restart) do_stop; sleep 0.3; do_start "${1:-}" ;;
    status)  do_status ;;
    use)     do_use "${1:-}" ;;
    *)
        echo "Annotator server manager"
        echo ""
        echo "Usage:"
        echo "  $(basename "$0") start [image.png]    start server (optionally swap image)"
        echo "  $(basename "$0") stop                 stop server"
        echo "  $(basename "$0") restart [image.png]  stop + start (optionally swap image)"
        echo "  $(basename "$0") status               check if running"
        echo "  $(basename "$0") use <image.png>      swap active image (then restart)"
        echo ""
        echo "Examples:"
        echo "  $(basename "$0") start"
        echo "  $(basename "$0") restart new_screen.png"
        echo "  $(basename "$0") use /path/to/other.png && $(basename "$0") restart"
        ;;
esac
