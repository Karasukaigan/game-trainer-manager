import os
import winreg
import subprocess

def find_and_run_steam():
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Valve\Steam") as key:
            steam_path = winreg.QueryValueEx(key, "InstallPath")[0]
            steam_exe = os.path.join(steam_path, "steam.exe")
            
            if os.path.exists(steam_exe):
                subprocess.Popen([steam_exe])
                print(f"成功启动Steam: {steam_exe}")
                return True
        common_paths = [
            os.path.expandvars("%ProgramFiles(x86)%\\Steam\\steam.exe"),
            os.path.expandvars("%ProgramFiles%\\Steam\\steam.exe"),
            os.path.expandvars("%LocalAppData%\\Programs\\Steam\\steam.exe")
        ]
        for path in common_paths:
            if os.path.exists(path):
                subprocess.Popen([path])
                print(f"成功启动Steam: {path}")
                return True
        print("未找到Steam安装路径")
        return False
    except Exception as e:
        print(f"查找Steam时出错: {e}")
        return False

if __name__ == "__main__":
    find_and_run_steam()