# Kiyo launcher guide

## Herdr Core

Run the launcher with `sh`. It requires `hc` and `jq`. Use the script's absolute path, a unique terminal name, and an existing absolute working directory:

```sh
sh "$skill_dir/scripts/launch.sh" --role lead --name "$name" --cwd "$workdir" -- "$task"
```

Use `--role worker` from inside Kiyo. The script uses the caller's `HC_TERMINAL_ID`, verifies it is a live Pi terminal, and passes it to `hc run --parent`. It adds reporting instructions and tells the lead how to launch workers with the same script. It prints the launch JSON after verifying the link; save its `address`.

If the script reports an error after launching, inspect the child with `hc get` or `hc read` before resending or retrying. A successful command does not prove the task is complete. See `hc --skill` for delivery and wait behavior.

Use `hc wait <child>` and `hc read --lines 100 <child>` to collect the result. To list your direct children, including finished ones, run `sh "$skill_dir/scripts/status.sh"`.

Once you've verified the final result and no follow-up is needed, run `sh "$skill_dir/scripts/stop.sh" "$child"` with the saved child address before replying, unless the user asked to keep the child running. The script rejects terminals that aren't direct children, skips finished children, and leaves the terminal record and output intact.


