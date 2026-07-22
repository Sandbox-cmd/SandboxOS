#!/bin/bash
# Michael — a woodshop-flavored terminal running the real Claude (free, your
# subscription), set up to design 3D-printable parts and drive your live Blender.
# Portable: lives next to his michael/ folder — wherever you put them both.
DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR/michael" || cd "$HOME"

# --- woodshop window: walnut background, warm oak text (Terminal.app) ---
osascript >/dev/null 2>&1 <<'OSA'
tell application "Terminal"
  set background color of front window to {9509, 6168, 3598}
  set normal text color of front window to {56283, 47031, 34181}
  set bold text color of front window to {60138, 41377, 15934}
  set cursor color of front window to {60138, 41377, 15934}
end tell
OSA

printf '\033]0;Michael — the woodshop\007'   # window title
clear

# --- the workshop guy: a cute bearded lumberjack with an axe (256-color) ---
# beanie coral, brim cream, face tan, beard brown, red-plaid flannel, steel axe
BEANIE='\033[38;5;209m'; BRIM='\033[38;5;223m'; SKIN='\033[38;5;180m'
BEARD='\033[38;5;130m'; SHIRT='\033[38;5;167m'; PLAID='\033[38;5;88m'
BLADE='\033[38;5;251m'; HANDLE='\033[38;5;137m'; DK='\033[38;5;52m'
G='\033[38;5;179m'; O='\033[38;5;101m'; B='\033[1m'; R='\033[0m'
S="${SHIRT}██"; P="${PLAID}██"    # flannel check cells
printf '\n'
printf "${BEANIE}          ▄▄▄▄▄▄▄▄${BLADE}      ▟████▙${R}\n"
printf "${BEANIE}        ▟████████████▙${BLADE} ◀██████▶${R}\n"
printf "${BEANIE}        ██████████████${BLADE}  ▜████▛${R}\n"
printf "${BRIM}         ▀▀▀▀▀▀▀▀▀▀▀▀${HANDLE}      ██${R}\n"
printf "${SKIN}          ██▀▀▀▀▀▀██${HANDLE}      ██${R}\n"
printf "${SKIN}          █  ${DK}●${SKIN}  ${DK}●${SKIN}  █${HANDLE}     ██${R}\n"
printf "${SKIN}          █   ${BEARD}▄▄▄${SKIN}  █${HANDLE}    ██${R}\n"
printf "${BEARD}         ▐███▄▄▄▄███▌${HANDLE}   ██${R}\n"
printf "${BEARD}          ▀██████████▀${HANDLE} ██${R}\n"
printf "${BEARD}            ▀▀████▀▀${R}\n"
printf "${SHIRT}        ▄████████████████▄${R}\n"
printf "        ${SHIRT}██${P}${S}${P}${S}${P}${S}${P}${SHIRT}██${R}\n"
printf "        ${SHIRT}██${S}${P}${S}${P}${S}${P}${S}${SHIRT}██${R}\n"
printf "        ${SHIRT}██${P}${S}${P}${S}${P}${S}${P}${SHIRT}██${R}\n"
printf "${SHIRT}        ▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀${R}\n\n"
printf "${G}${B}        M I C H A E L${R}\n"
printf "${O}        ·  the woodshop  ·${R}\n\n"
printf "${O}     pull up a stool — keep Blender open.${R}\n\n"

# open the scratch canvas so Blender is live before Michael greets
open -a Blender "$DIR/michael/newsession.blend"

# snap the shop into place — Blender up top, Terminal down below. Runs in the
# background: it waits for Blender's window to boot, then splits the screen.
# Backgrounded before the exec below so it survives the handover to Claude.
python3 "$DIR/michael/split_shop.py" >/dev/null 2>&1 &

# open the conversation so Michael greets first (pings Blender, asks the material),
# then hand over to interactive chat. bypassPermissions so his Blender/build commands
# run without asking you to approve each one (your shop, your machine).
exec claude --permission-mode bypassPermissions \
  --settings "{\"tui\":\"default\",\"statusLine\":{\"type\":\"command\",\"command\":\"bash $DIR/michael/statusline.sh\"}}" \
  "hey michael, i just opened the shop"
