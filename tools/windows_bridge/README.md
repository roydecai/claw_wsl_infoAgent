# Windows Bridge for WSL OpenClaw

这个目录提供一个本地桥接服务，让运行在 WSL 内的 OpenClaw 可以调用 Windows 的终端和基础 UI 自动化。

## 目录

- `windows_bridge_server.py`：Windows 侧常驻 HTTP 服务（标准库实现）
- `windows_bridge_server.ps1`：Windows 启动包装脚本
- `wsl_bridge.sh`：WSL 侧调用脚本
- `windows_bridge.log`：服务请求日志（运行后生成）

## 1) 在 Windows 启动桥接服务

在 Windows PowerShell 中执行：

```powershell
cd D:\projects\info_gatherer\tools\windows_bridge
$env:WINDOWS_BRIDGE_TOKEN = "replace-with-a-strong-token"
# 可选：允许的命令前缀，逗号分隔
# $env:WINDOWS_BRIDGE_ALLOWED_PREFIXES = "Get-,ls,dir,pwd,echo,whoami,ipconfig,tasklist,wt,cmd /c"
powershell -ExecutionPolicy Bypass -File .\windows_bridge_server.ps1 -Port 8765
```

也可以直接运行 Python：

```powershell
$env:WINDOWS_BRIDGE_TOKEN = "replace-with-a-strong-token"
$env:WINDOWS_BRIDGE_PORT = "8765"
python .\windows_bridge_server.py
```

## 2) 在 WSL 调用

在 WSL Shell 中执行：

```bash
cd /mnt/d/projects/info_gatherer/tools/windows_bridge
chmod +x ./wsl_bridge.sh
export WINDOWS_BRIDGE_TOKEN='replace-with-a-strong-token'
# 可选：强制指定 Windows 主机 IP
# export WINDOWS_BRIDGE_HOST=127.0.0.1
# export WINDOWS_BRIDGE_PORT=8765
```

## 3) 快速验证

```bash
./wsl_bridge.sh health
./wsl_bridge.sh shell "whoami"
./wsl_bridge.sh shell "Get-Process | Select-Object -First 3"
./wsl_bridge.sh ui launch_windows_terminal
./wsl_bridge.sh ui open_notepad_and_type "hello from wsl"
```

## API 约定

- `GET /health`：健康检查
- `POST /run`：执行任务
  - shell:
    - `{"token":"...","type":"shell","cmd":"Get-Process"}`
  - ui:
    - `{"token":"...","type":"ui","action":"launch_windows_terminal"}`
    - `{"token":"...","type":"ui","action":"open_notepad_and_type","text":"hello"}`

## 安全说明

- 服务仅监听 `127.0.0.1`（可通过 `WINDOWS_BRIDGE_BIND_HOST` 调整）
- 每次请求必须带 token
- shell 命令做了前缀白名单 + 危险模式拦截
- 请求会写入本地日志，便于审计

如果要放宽可执行命令，请优先增补 `WINDOWS_BRIDGE_ALLOWED_PREFIXES`，不要关闭限制。
