@SETLOCAL
@IF NOT DEFINED NODE_PATH (
  @SET "NODE_PATH=C:\Users\acer\Documents\Codex\2026-09-03\files-mentioned-by-the-user-ai\outputs\mandate-warrant\frontend\node_modules\.pnpm\vite@8.2.2\node_modules\vite\node_modules;C:\Users\acer\Documents\Codex\2026-09-03\files-mentioned-by-the-user-ai\outputs\mandate-warrant\frontend\node_modules\.pnpm\vite@8.2.2\node_modules;C:\Users\acer\Documents\Codex\2026-09-03\files-mentioned-by-the-user-ai\outputs\mandate-warrant\frontend\node_modules\.pnpm\node_modules"
) ELSE (
  @SET "NODE_PATH=C:\Users\acer\Documents\Codex\2026-09-03\files-mentioned-by-the-user-ai\outputs\mandate-warrant\frontend\node_modules\.pnpm\vite@8.2.2\node_modules\vite\node_modules;C:\Users\acer\Documents\Codex\2026-09-03\files-mentioned-by-the-user-ai\outputs\mandate-warrant\frontend\node_modules\.pnpm\vite@8.2.2\node_modules;C:\Users\acer\Documents\Codex\2026-09-03\files-mentioned-by-the-user-ai\outputs\mandate-warrant\frontend\node_modules\.pnpm\node_modules;%NODE_PATH%"
)
@IF EXIST "%~dp0\node.exe" (
  "%~dp0\node.exe"  "%~dp0\..\vite\bin\vite.js" %*
) ELSE (
  @SET PATHEXT=%PATHEXT:;.JS;=;%
  node  "%~dp0\..\vite\bin\vite.js" %*
)
