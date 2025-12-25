# Sandbox

## Setup

1. Run `./build.sh` (downloads `sandbox`/`sandbox_interactive`, builds `noj-c-cpp`, `noj-py3`, `noj-interactive`, `noj-custom-checker-scorer`, `router` images).
2. Update `.config/submission.json` `working_dir` to `/path/to/Normal-OJ/Sandbox/submissions`.
3. Update `.config/submission.json` `host_root` to `/path/to/Normal-OJ/Sandbox`.
4. Adjust interactive limits in `.config/interactive.json` if needed (`outputLimitBytes`, `maxTeacherNewFiles`).

## before push

```bash
yapf . -ri
```
