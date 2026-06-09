## [ERR-20260608-001] Windows sandbox helper launch

**Logged**: 2026-06-08T00:00:00+08:00
**Priority**: low
**Status**: resolved
**Area**: infra

### Summary
Parallel read-only project inspection failed before the commands started.

### Error
```
windows sandbox: orchestrator_helper_launch_canceled: ShellExecuteExW failed to launch setup helper: 1223
```

### Context
- Initial `rg`, `git status`, and virtual-environment checks were affected.
- No project command executed and no files were changed by the failed calls.

### Suggested Fix
Retry the same read-only commands with the controlled sandbox escalation path.

### Metadata
- Reproducible: unknown
- Related Files: none

### Resolution
- **Resolved**: 2026-06-08T00:00:00+08:00
- **Notes**: Retried with approved read-only escalation and continued normally.

---
## [ERR-20260608-004] rust_toolchain_unavailable

**Logged**: 2026-06-08T22:12:00+08:00
**Priority**: low
**Status**: pending
**Area**: tests

### Summary
The local environment cannot execute the `cc-switch` Rust tests because Cargo and rustc are not installed or not on PATH.

### Error
```
The term 'cargo' is not recognized as a name of a cmdlet, function, script file, or executable program.
The term 'rustc' is not recognized as a name of a cmdlet, function, script file, or executable program.
```

### Context
- Attempted to verify the targeted protocol conversion tests in `cc-switch/src-tauri`.

### Suggested Fix
Install a Rust toolchain compatible with the repository's declared Rust 1.85 minimum before running Cargo tests.

### Metadata
- Reproducible: yes
- Related Files: cc-switch/src-tauri/Cargo.toml

---
## [ERR-20260608-002] stale_python_virtualenv

**Logged**: 2026-06-08T22:10:00+08:00
**Priority**: medium
**Status**: pending
**Area**: tests

### Summary
The repository `.venv` cannot run because its base Python 3.14 executable no longer exists.

### Error
```
did not find executable at 'C:\Users\oucan\AppData\Local\Programs\Python\Python314\python.exe'
```

### Context
- Attempted to run the Codex protocol unit tests with `.venv\Scripts\python.exe`.
- The checked-in workspace virtual environment is stale.

### Suggested Fix
Recreate `.venv` with the currently installed Python interpreter.

### Metadata
- Reproducible: yes
- Related Files: .venv/pyvenv.cfg

---

## [ERR-20260608-003] nested_repo_dubious_ownership

**Logged**: 2026-06-08T22:10:00+08:00
**Priority**: low
**Status**: pending
**Area**: infra

### Summary
Git status for the nested `cc-switch` repository is blocked by sandbox ownership checks.

### Error
```
fatal: detected dubious ownership in repository at 'C:/Users/oucan/Documents/vscode/claude_code模型管理器/cc-switch'
```

### Context
- The workspace is running under the `CodexSandboxOffline` Windows account.
- No global Git configuration was changed because repository inspection did not require it.

### Suggested Fix
Run Git for this repository under its owning user, or explicitly configure the directory as safe when needed.

### Metadata
- Reproducible: yes
- Related Files: cc-switch/.git

---

## [ERR-20260608-002] PowerShell GBK emoji output

**Logged**: 2026-06-08T00:00:00+08:00
**Priority**: low
**Status**: resolved
**Area**: docs

### Summary
A README validation script tried to print emoji to a GBK PowerShell console.

### Error
```
UnicodeEncodeError: 'gbk' codec can't encode character
```

### Suggested Fix
Avoid echoing emoji during validation or set Python output encoding to UTF-8.

### Resolution
- **Resolved**: 2026-06-08T00:00:00+08:00
- **Notes**: Validation was rerun with ASCII-only output.

---

## [ERR-20260608-001] PyQt6 empty alignment construction

**Logged**: 2026-06-08T00:00:00+08:00
**Priority**: low
**Status**: resolved
**Area**: tests

### Summary
A temporary layout experiment used `Qt.Alignment()`, which is not available in PyQt6.

### Error
```
AttributeError: type object 'Qt' has no attribute 'Alignment'
```

### Suggested Fix
Use `Qt.AlignmentFlag(0)` when an empty PyQt6 alignment value is required.

### Metadata
- Reproducible: yes
- Related Files: tests/test_ui_smoke.py

### Resolution
- **Resolved**: 2026-06-08T00:00:00+08:00
- **Notes**: The experiment was rerun with the PyQt6-compatible enum value.

---

## [ERR-20260608-002] PowerShell no-match check

**Logged**: 2026-06-08T00:00:00+08:00
**Priority**: low
**Status**: resolved
**Area**: infra

### Summary
A final `rg` no-match check used shell syntax that was split incorrectly by the command wrapper.

### Error
```
The term 'exit' is not recognized as a name of a cmdlet
```

### Context
- The source search itself returned no matches.
- The failure came from the trailing `|| exit 0` compatibility expression.

### Suggested Fix
Use `$LASTEXITCODE` with a native PowerShell conditional for expected no-match results.

### Metadata
- Reproducible: yes
- Related Files: none

### Resolution
- **Resolved**: 2026-06-08T00:00:00+08:00
- **Notes**: Replaced the expression with a PowerShell-native conditional.

---

## [ERR-20260608-003] PowerShell rg quoted pattern

**Logged**: 2026-06-08T00:00:00+08:00
**Priority**: low
**Status**: resolved
**Area**: infra

### Summary
A completion-audit search used a quoted regex that PowerShell truncated.

### Error
```
rg: regex parse error: unclosed group
```

### Context
- The failed command was read-only.
- Source compilation and the complete test suite had already passed.

### Suggested Fix
Use separate fixed-string `-e` arguments instead of one shell-escaped regex.

### Metadata
- Reproducible: yes
- Related Files: none

### Resolution
- **Resolved**: 2026-06-08T00:00:00+08:00
- **Notes**: Re-ran ordinary patterns successfully and used PowerShell `Select-String -SimpleMatch` for strings containing nested quotes.

### Recurrence
- Recurrence-Count: 3

---

## [ERR-20260607-001] local Codex proxy integration test

**Logged**: 2026-06-07T00:00:00+08:00
**Priority**: high
**Status**: resolved
**Area**: tests

### Summary
The first end-to-end random-port proxy test returned HTTP 500.

### Error
```
AssertionError: 500 != 200
```

### Context
- The pure Responses/Chat conversion tests passed.
- Failure occurs only through the threaded local HTTP router and mock upstream.
- Related files: `src/services/codex_proxy_server.py`, `tests/test_codex_proxy_server.py`.

### Suggested Fix
Capture the router error body and log callback, then correct HTTP client or handler lifecycle behavior.

### Metadata
- Reproducible: yes
- Related Files: src/services/codex_proxy_server.py, tests/test_codex_proxy_server.py

### Resolution
- **Resolved**: 2026-06-07T00:00:00+08:00
- **Notes**: Disabled HTTPX `trust_env` and made the router use only the proxy explicitly selected in the application.

---

## [ERR-20260607-004] QTabWidget corner alignment timing

**Logged**: 2026-06-07T00:00:00+08:00
**Priority**: low
**Status**: resolved
**Area**: frontend

### Summary
Immediate corner-widget alignment was overwritten by Qt after `showEvent`.

### Error
```
AssertionError: 11 != 10
```

### Context
- The tab bar and authentication button were both 36 pixels high.
- Qt completed another internal layout pass after `showEvent`, moving the corner widget one pixel upward.

### Suggested Fix
Repeat alignment with `QTimer.singleShot(0, ...)` after Qt finishes the current layout cycle.

### Metadata
- Reproducible: yes
- Related Files: src/ui/main_window.py, tests/test_ui_smoke.py

### Resolution
- **Resolved**: 2026-06-07T00:00:00+08:00
- **Notes**: Alignment now runs immediately and once more at the end of the event cycle.

---

## [ERR-20260607-003] Windows npm command lookup

**Logged**: 2026-06-07T00:00:00+08:00
**Priority**: medium
**Status**: resolved
**Area**: backend

### Summary
Direct `subprocess.run(["npm", ...])` failed on Windows because npm is exposed through `npm.cmd`.

### Error
```
FileNotFoundError: [WinError 2] 系统找不到指定的文件。
```

### Context
- Unit tests passed because version lookups were mocked.
- The real Claude lookup returned `None`; the Codex lookup raised from `_run_hidden`.

### Suggested Fix
Run npm queries through `cmd.exe /d /c` on Windows and return `None` when the query process cannot start.

### Metadata
- Reproducible: yes
- Related Files: src/services/claude_service.py, src/services/codex_service.py

### Resolution
- **Resolved**: 2026-06-07T00:00:00+08:00
- **Notes**: Both services now use the Windows command interpreter for npm version queries.

---

## [ERR-20260607-002] apply_patch stale context

**Logged**: 2026-06-07T00:00:00+08:00
**Priority**: low
**Status**: resolved
**Area**: frontend

### Summary
An interface style patch failed because the interrupted session had already applied the requested changes.

### Error
```
apply_patch verification failed: Failed to find expected lines
```

### Context
- The patch used an earlier snapshot of `src/ui/styles.py`.
- The current file already contained compact light-blue tabs and buttons.

### Suggested Fix
Read the current file after an interruption before applying a patch based on prior context.

### Metadata
- Reproducible: no
- Related Files: src/ui/styles.py, src/ui/widgets/auth_settings_dialog.py

### Resolution
- **Resolved**: 2026-06-07T00:00:00+08:00
- **Notes**: Inspected the current files and only added the missing regression tests.

---
## [ERR-20260608-001] rg_unavailable

**Logged**: 2026-06-08T22:00:00+08:00
**Priority**: low
**Status**: resolved
**Area**: infra

### Summary
Repository search initially failed because ripgrep is not installed in the PowerShell environment.

### Error
```
The term 'rg' is not recognized as a name of a cmdlet, function, script file, or executable program.
```

### Context
- Attempted to locate Responses API and Chat Completions conversion code with `rg`.
- Environment: Windows 11, PowerShell.

### Suggested Fix
Use `Get-ChildItem` with `Select-String` as the local fallback.

### Metadata
- Reproducible: yes
- Related Files: .learnings/ERRORS.md

### Resolution
- **Resolved**: 2026-06-08T22:00:00+08:00
- **Notes**: Continued repository inspection using native PowerShell search.

---
