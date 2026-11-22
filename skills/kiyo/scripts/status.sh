#!/bin/sh
set -eu

fail() {
    printf 'kiyo %s: %s\n' "status" "$*" >&2
    exit 1
}

[ "$#" -eq 0 ] || fail 'usage: sh status.sh'

[ -n "${HC_TERMINAL_ID:-}" ] || fail 'HC_TERMINAL_ID is missing'
command -v hc >/dev/null 2>&1 || fail 'hc is required'
command -v jq >/dev/null 2>&1 || fail 'jq is required'

current=$(hc get --json "$HC_TERMINAL_ID") || fail 'could not look up the current terminal'
parent=$(printf '%s\n' "$current" | jq -er '.address | strings | select(length > 0)') ||
    fail 'could not resolve the current terminal address'

terminals=$(hc ls --all --json) || fail 'could not list terminals'
printf '%s\n' "$terminals" | jq --arg parent "$parent" '
    ($parent | split("/") | .[:-1]) as $machine
    | [.terminals[]
        | select(.parent == $parent and (.address | split("/") | .[:-1]) == $machine)
        | {address, name, state, status, exit_code}]
'
