# Legacy Move Map (planned)

This maps legacy/reference artifacts to their legacy locations. Moves below have been executed.

## Code/UI (moved)
- main.py -> legacy/ui/main.py (PyQt desktop entry, legacy)
- ui/ -> legacy/ui/ui/ (PyQt widgets, legacy)
- web_server.py -> legacy/web_server.py (legacy Flask UI)
- webui-old/ -> legacy/webui-old/ (old web UI)
- isolated_test.py -> legacy/tests/isolated_test.py (one-off script)
- test_qwidget.py -> legacy/tests/test_qwidget.py (legacy UI test)

## Docs / notes (moved)
- Webui-Refactor.txt -> legacy/Docs/Webui-Refactor.txt (historical note)
- BUILD_AND_DEPLOY.md -> legacy/Docs/BUILD_AND_DEPLOY.md (deprecated instructions)
- build_and_deploy.bat -> legacy/Docs/build_and_deploy.bat (deprecated helper)
- build_and_deploy.sh -> legacy/Docs/build_and_deploy.sh (deprecated helper)
- UNRAID.md -> legacy/Docs/UNRAID.md (archived)

## Keep in place (for now)
- DEPLOYMENT_CHECKLIST.md, DEPLOYMENT_INDEX.md, DOCKER*.md, README*.md, QUICK_START.md (still relevant to ops/deploy)
- tests/ (pytest suite) stays in place
- config/ (mounted volume expectations)

## Stubbing strategy (executed)
- Originals replaced with stubs where applicable (main.py, web_server.py) raising ImportError.
