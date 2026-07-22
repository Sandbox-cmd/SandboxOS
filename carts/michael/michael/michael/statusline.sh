#!/bin/bash
# Michael's woodshop status bar: project · blender link · skills · ctx.
# Claude Code pipes session JSON on stdin; we print one line.
input=$(cat)

# ---- colours -------------------------------------------------------------
# No background — the row is tinted by the font colour alone. Greyish lilac text is
# what marks it as fixed UI; nothing is painted behind it.
#
# NB: the in-line reset is TXT, not \033[39m. \033[39m restores the terminal's default
# foreground (near-white on a dark theme), which would break the row back out of lilac
# halfway through. Only the blender dot gets its own colour — that's live signal.
TXT='\033[38;2;170;160;190m'  # all text — greyish lilac
GRN='\033[38;5;71m'           # blender online — unchanged from the original
RED='\033[38;5;131m'          # blender off — unchanged from the original
R="$TXT"                      # in-line reset = back to lilac
RESET='\033[0m'               # full reset — end of row only

cwd=$(printf '%s' "$input" | jq -r '.workspace.current_dir // .cwd // empty' 2>/dev/null)
[ -z "$cwd" ] && cwd="$PWD"
proj=$(basename "$cwd")
# friendly shop name for this project
[ "$proj" = "michael-app" ] && proj="Michael's Workshop"

# your custom skills (the live, project-relevant ones; built-ins are always on).
# Two dirs feed this: ~/.claude/skills (yours everywhere) and the project's own
# .claude/skills. A dir only counts as a skill if it holds a SKILL.md.
skills_in() {
  [ -d "$1" ] || return
  for d in "$1"/*/; do [ -f "$d/SKILL.md" ] && basename "$d"; done
}
# NB: paste -d takes a LIST of delimiters and cycles them, so -d', ' alternates
# comma/space and only looks right with two entries. Join on ',' then space it out.
sk=$( { skills_in "$HOME/.claude/skills"; skills_in "$cwd/.claude/skills"; } \
      | sort -u | paste -sd',' - | sed 's/,/, /g')
[ -z "$sk" ] && sk="—"

# permission mode. NOT in the status line JSON — Claude Code doesn't send it. But it
# IS in the transcript, on type='permission-mode' records and on every user message,
# and that's the LIVE value: settings.json only holds permissions.defaultMode, which
# goes stale the moment you shift-tab.
# Tail, never scan: the transcript runs to megabytes and this script runs every render.
# 400 lines is ~6x the observed gap between permissionMode records, so it's a safe window.
tp=$(printf '%s' "$input" | jq -r '.transcript_path // empty' 2>/dev/null)
mode=""
if [ -n "$tp" ] && [ -f "$tp" ]; then
  raw=$(tail -n 400 "$tp" 2>/dev/null \
        | grep -o '"permissionMode":"[a-zA-Z]*"' | tail -1 | cut -d'"' -f4)
  case "$raw" in
    bypassPermissions) mode="bypass"    ;;
    acceptEdits)       mode="accept"    ;;
    plan)              mode="plan"      ;;
    default)           mode="ask"       ;;
    "")                mode=""          ;;
    *)                 mode="$raw"      ;;
  esac
fi

# is the Blender connector live?
if python3 -c 'import socket; socket.create_connection(("127.0.0.1",9876),0.3).close()' 2>/dev/null; then
  bl="${GRN}● online${R}"
else
  bl="${RED}● off${R}"
fi

# context fill: a little sawdust gauge of the window.
# NB: v2.1.209 does NOT send .context_window.used_tokens / .max_tokens — the real
# fields are .context_window_size and .used_percentage. Reading the old names silently
# yields empty and falls through to the % form, so only ever show what we actually get.
ctx=""
pct=$(printf '%s' "$input" | jq -r '.context_window.used_percentage // empty' 2>/dev/null)
size=$(printf '%s' "$input" | jq -r '.context_window.context_window_size // empty' 2>/dev/null)
if [ -n "$pct" ]; then
  pi=$(printf '%.0f' "$pct")
  filled=$((pi / 10)); [ "$filled" -gt 10 ] && filled=10
  empty=$((10 - filled))
  bar=""
  for ((j=0; j<filled; j++)); do bar+="█"; done
  for ((j=0; j<empty; j++)); do bar+="░"; done
  if [ -n "$size" ] && [ "$size" -gt 0 ] 2>/dev/null; then
    ctx="ctx: [$bar] ${pi}% of $((size / 1000))k"
  else
    ctx="ctx: [$bar] ${pi}%"
  fi
fi

# ---- assemble the row ----------------------------------------------------
# Two clusters: the left one sits flush left with fixed gaps, ctx is anchored right
# (short of the edge by RMARGIN), and all the slack goes in between. Fixed gaps on
# the left matter — if the left cluster were spread too, every tick of the ctx gauge
# would re-flow the whole row. This way only the middle gap breathes.
LGAP=4                       # gap inside the left cluster
RMARGIN=3                    # padding between ctx and the right edge
left=("${TXT}🪵 ${proj}${R}")
[ -n "$mode" ] && left+=("${TXT}mode: ${mode}${R}")
left+=(
  "${TXT}blender${R} ${bl}"
  "${TXT}custom skills ${sk}${R}"
)
right=()
[ -n "$ctx" ] && right+=("${TXT}${ctx}${R}")

# Claude Code sets $COLUMNS (v2.1.153+); tput is the fallback.
cols=${COLUMNS:-0}
case "$cols" in ''|*[!0-9]*) cols=0 ;; esac
[ "$cols" -eq 0 ] && cols=$(tput cols 2>/dev/null || echo 0)
case "$cols" in ''|*[!0-9]*) cols=0 ;; esac

# %b turns the \033 escapes into real ESC bytes. \037 (unit separator) delimits the
# segments and \036 (record separator) splits left cluster from right — neither can
# occur inside a segment. Python does the layout because it needs the same
# ANSI-stripped width measure — 🪵 counts as two cells.
line=$( { printf '%b\037' "${left[@]}"
          printf '\036'
          [ ${#right[@]} -gt 0 ] && printf '%b\037' "${right[@]}"
        } | python3 -c '
import sys, re, unicodedata

def width(s):
    s = re.sub(r"\033\[[0-9;]*m", "", s)
    return sum(2 if unicodedata.east_asian_width(c) in ("W", "F") else 1 for c in s)

MIN = 2                       # gap floor when the row is too tight
cols, lgap, rmargin = int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3])
lpart, _, rpart = sys.stdin.read().partition("\036")
left  = [s for s in lpart.split("\037") if s]
right = [s for s in rpart.split("\037") if s]

lstr = (" " * lgap).join(left)
rstr = (" " * lgap).join(right)
if not rstr:                  # nothing to anchor — just the left cluster
    sys.stdout.write(lstr)
    raise SystemExit

slack = cols - width(lstr) - width(rstr) - rmargin
# too narrow to anchor — fall back to a fixed gap and let it run long
sys.stdout.write(lstr + " " * (slack if cols > 0 and slack >= MIN else MIN) + rstr)
' "$cols" "$LGAP" "$RMARGIN" 2>/dev/null)

printf "%s${RESET}" "$line"
