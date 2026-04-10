# Obsidian右键菜单

✨ 为 Windows 资源管理器添加一个简洁好用的右键菜单项：

```text
在任意文件夹空白处右键 → Open in Obsidian
```

📂 这个工具可以在需要时把当前文件夹转换成 Obsidian 仓库（vault），然后直接用 Obsidian 打开。

## 🚀 功能说明

当你在文件夹空白处右键，并选择 **Open in Obsidian** 时，脚本会自动执行以下步骤：

1. 📍 从 Windows 资源管理器获取当前文件夹路径。
2. 🔍 检查该文件夹是否已经包含 `.obsidian` 目录。
3. 📥 如果没有，就把模板 `.obsidian` 目录复制进去。
4. 🛑 关闭当前正在运行的 Obsidian 进程，避免旧的 vault 状态或配置覆盖问题。
5. 📝 更新 Obsidian 的仓库列表配置文件：

```text
%APPDATA%\obsidian\obsidian.json
```

6. ✅ 将当前选中的文件夹标记为要打开的 vault。
7. 🚀 启动 Obsidian。

🎯 最终效果：你右键点击的那个文件夹，会直接作为当前活动仓库在 Obsidian 中打开。

## ⚡ 快速开始

下载或克隆本仓库后，运行：

```powershell
python open_in_obsidian_right_click.py
```

🖱️ 这会把 **Open in Obsidian** 添加到 Windows 资源管理器中文件夹背景的右键菜单中。

💡 在 Windows 11 中，这个菜单项可能会出现在：

```text
Show more options
```

下面。

## 📋 运行要求

这个项目刻意保持简单、轻量，不需要额外安装依赖，也不需要复杂配置。

你只需要：

- 🪟 Windows
- 🐍 Python 3.9 或更新版本
- 🧠 Obsidian

## 📦 无额外依赖

目标就是在一台全新的 Windows 机器上也能轻松运行：

- 🚫 不需要 `pip install`
- 🚫 不需要包管理器
- 🚫 不需要构建步骤
- 🚫 一般情况下不需要管理员权限
- 🚫 不需要从外部下载模板

## ⚙️ 默认行为

脚本会自动检测常见的 Obsidian 安装路径，也会优先检查下面这个路径：

```text
D:\ProgramFiles\Obsidian\Obsidian.exe
```

📁 仓库中已经自带一个默认的 `.obsidian` 模板目录：

```text
ObsidianRightClickMenu\.obsidian
```

当目标文件夹还不是 vault 时，脚本会先把这个模板复制进去，再启动 Obsidian。

## 🛠️ 自定义 Obsidian 路径

如果你的 Obsidian 安装在别的位置，可以这样运行：

```powershell
python open_in_obsidian_right_click.py --obsidian-exe "C:\Users\you\AppData\Local\Programs\Obsidian\Obsidian.exe"
```

## 🎨 自定义 Vault 模板

如果你想使用自己的默认 `.obsidian` 模板，可以这样运行：

```powershell
python open_in_obsidian_right_click.py --template-dir "D:\MyDefaultVault\.obsidian"
```

这是可选功能。若你希望每个新建 vault 一开始就带上你偏好的配置，它会很有用，例如：

- 🔌 核心插件设置
- 🎨 外观设置
- 🧭 工作区布局
- 🧩 社区插件目录（如果你选择一并包含）

## 🏷️ 自定义右键菜单名称

```powershell
python open_in_obsidian_right_click.py --menu-name "Open Folder as Obsidian Vault"
```

## 🗑️ 删除右键菜单项

```powershell
python open_in_obsidian_right_click.py --remove
```

这会从当前 Windows 用户的资源管理器右键菜单中移除该项。

## 📁 写入的文件与注册表位置

Python 脚本会把一个 PowerShell 辅助脚本写入：

```text
%LOCALAPPDATA%\ObsidianRightClickMenu\OpenFolderAsObsidianVault.ps1
```

同时，它会把右键菜单项写入当前用户的注册表：

```text
HKEY_CURRENT_USER\Software\Classes\Directory\Background\shell\OpenInObsidian
```

🔐 一般情况下不需要管理员权限。

## ❓ 为什么不直接用 `obsidian://open`？

对于 Obsidian 已经认识的 vault，URI 链接通常很好用。

⚠️ 但对于全新的文件夹，这种方式并不稳定，因为正在运行的 Obsidian 进程可能还没有加载这个新 vault。于是就可能出现下面这类报错：

```text
Vault not found
Unable to find a vault for the URL obsidian://open/?vault=...
```

✅ 这个项目的做法是在启动 Obsidian 之前，先更新它的 vault 配置，因此行为会更稳定、更可预测。

## 📝 说明

这个工具会在使用右键菜单时主动关闭并重新打开 Obsidian。这样做是为了保证行为一致，因为 Obsidian 会在启动时重新读取更新后的 vault 列表。

💾 在修改 Obsidian 配置之前，辅助脚本会先创建一个备份文件：

```text
%APPDATA%\obsidian\obsidian.json.bak
```

## 📄 许可证

MIT
