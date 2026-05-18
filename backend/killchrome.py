import subprocess
import time


def main():
    time.sleep(1)
    subprocess.run(
        ["taskkill", "/IM", "chrome.exe", "/F", "/T"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )


if __name__ == "__main__":
    main()
