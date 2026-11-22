#!/bin/sh
set -eu

fail() {
    printf 'kiyo %s: %s\n' "stop" "$*" >&2
    exit 1
}

[ "$#" -eq 1 ] || fail 'usage: sh stop.sh CHILD_ADDRESS'
case "$1" in ''|-*) fail 'pass the saved child address' ;; esac

[ -n "${HC_TERMINAL_ID:-}" ] || fail 'HC_TERMINAL_ID is missing'
command -v hc >/dev/null 2>&1 || fail 'hc is required'
command -v jq >/dev/null 2>&1 || fail 'jq is required'

current=$(hc get --json "$HC_TERMINAL_ID") || fail 'could not look up the current terminal'
parent=$(printf '%s\n' "$current" | jq -er '.address | strings | select(length > 0)') ||
    fail 'could not resolve the current terminal address'

child=$1
record=$(hc get --json "$child") || fail "could not look up $child"
state=$(printf '%s\n' "$record" | jq -er --arg child "$child" --arg parent "$parent" '
    select(.address == $child and .parent == $parent)
    | select((.address | split("/") | .[:-1]) == ($parent | split("/") | .[:-1]))
    | .state | select(. == "finished" or . == "live")
') || fail "$child is not a verified direct child of $parent"
if [ "$state" = finished ]; then
    printf '%s already exited\n' "$child"
    exit 0
fi
if ! hc kill "$child"; then
    fail "could not stop $child; inspect its state with hc get"
fi
