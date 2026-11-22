#!/bin/sh
set -eu

usage() {
    printf '%s\n' 'Usage: sh launch.sh --role lead|worker --name NAME --cwd ABSOLUTE_DIR -- TASK'
}

fail() {
    printf 'kiyo launch: %s\n' "$*" >&2
    exit 1
}

role= name= workdir=
while [ "$#" -gt 0 ]; do
    case "$1" in
        --role|--name|--cwd)
            [ "$#" -ge 2 ] || fail "$1 requires a value"
            case "$1" in
                --role) role=$2 ;;
                --name) name=$2 ;;
                --cwd) workdir=$2 ;;
            esac
            shift 2 ;;
        -h|--help) usage; exit 0 ;;
        --) shift; break ;;
        -*) fail "unknown option: $1" ;;
        *) break ;;
    esac
done

case "$role" in lead|worker) ;; *) fail '--role must be lead or worker' ;; esac
[ -n "$name" ] || fail '--name is required'
case "$workdir" in /*) ;; *) fail '--cwd must be absolute' ;; esac
[ -d "$workdir" ] || fail '--cwd must be an existing directory'
[ "$#" -eq 1 ] || fail 'pass one task argument'
case "$1" in *[![:space:]]*) ;; *) fail 'task must not be empty' ;; esac
[ -n "${HC_TERMINAL_ID:-}" ] || fail 'HC_TERMINAL_ID is missing'
command -v hc >/dev/null 2>&1 || fail 'hc is required'
command -v jq >/dev/null 2>&1 || fail 'jq is required to parse hc output'

current=$(hc get --json "$HC_TERMINAL_ID") || fail 'could not look up the current terminal'
parent=$(printf '%s\n' "$current" | jq -er '
    select(.state == "live" and (.foreground.name == "pi" or .status.app == "pi"))
    | .address | strings | select(length > 0)
') || fail "$HC_TERMINAL_ID is not a live Pi terminal"

task=$(printf 'Assignment:\n%s\n\nReport your result or blocker to your parent with `hc send %s "<report>"`.\n' "$1" "$parent")
if [ "$role" = lead ]; then
    script_dir=$(CDPATH= cd -P "$(dirname "$0")" && pwd -P) || fail 'could not resolve launcher directory'
    task="$task
You are Kiyo. Read $script_dir/../SKILL.md. If you delegate, run the following from your own session:
sh \"$script_dir/launch.sh\" --role worker --name \"\$name\" --cwd \"\$workdir\" -- \"\$task\"
The script uses your HC_TERMINAL_ID as the worker's parent; $parent is only the address for your report. Do not use another launcher. Verify each worker's result, then run sh \"$script_dir/stop.sh\" \"\$child\" with its saved address, unless the user explicitly asked to keep it running."
else
    task="$task
Do not launch more agents."
fi

launch=$(hc run --json --bg --parent "$parent" --name "$name" --cwd "$workdir" pi "$task") ||
    fail "hc run failed; inspect terminal name $name before retrying"
child=$(printf '%s\n' "$launch" | jq -er '.address | strings | select(length > 0)') ||
    fail "hc did not return a child address; inspect terminal name $name before retrying"
record=$(hc get --json "$child") || fail "could not look up child $child; inspect it before retrying"
printf '%s\n' "$record" | jq -e --arg parent "$parent" '.parent == $parent' >/dev/null ||
    fail "could not verify child $child is linked to $parent; inspect it before retrying"

printf '%s\n' "$launch"
if printf '%s\n' "$launch" | jq -e '.first_message.sent == false' >/dev/null; then
    fail "hc reports the task was not sent; inspect child $child before retrying"
fi
