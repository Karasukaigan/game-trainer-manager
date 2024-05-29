# Game Trainer Manager

[English](./README.md) | 简体中文

<img src="app/resources/logo.png" alt="Logo" width="200" height="200">

**Game Trainer Manager（游戏修改器管理器）** 是一个轻量化的软件，专门用于管理`.exe`格式的游戏修改器文件。它提供了下载、保存、删除等功能，支持简体中文和英文，完全免费且开源（请勿将其用于商业用途）。

## 功能特点

- 管理 `.exe` 格式的游戏修改器
- 下载、保存和删除修改器
- 将修改器文件名自动翻译成中文
- 多语言游戏名查询
- 多语言UI界面（简体中文和英文）
- 轻量化
- 免费和开源

![screenshot](app/resources/screenshot_en.png)

## 安装方法

您可以通过以下两种方式下载软件：

1. **直接从 Releases 下载：**
   - 进入 [Releases](https://github.com/your-repo/releases) 部分并下载安装包。

2. **克隆存储库并在本地运行：**
   - 将存储库克隆到本地机器：
     ```bash
     git clone https://github.com/your-repo/game-trainer-manager.git
     ```
   - 导航到项目根目录并运行以下命令：

     ```bash
     # 创建名为 'venv' 的虚拟环境
     python -m venv venv

     # 激活虚拟环境
     venv\Scripts\activate

     # 安装所需的依赖项
     pip install -r requirements.txt

     # 运行应用程序
     python .\main.py
     ```

## 主要技术栈

- **PyQt6**：用于构建GUI框架。
- **requests + retrying + beautifulsoup4**：用于获取更新。
- **gettext**：用于实现多语言的UI页面。
- **PyInstaller**：用于将Python程序打包成可执行文件。
- **Inno Setup**：用于制作安装包。

## 调试模式

在项目根目录或者软件的`_internal`目录里找到`config.ini`这个文件，然后将  
```
debugmode = false
```
改为  
```
debugmode = true
```
即可打开调试模式。  