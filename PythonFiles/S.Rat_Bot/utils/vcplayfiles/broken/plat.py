import subprocess
from colorama import init, Fore, Style
init(autoreset=True)

print(Fore.YELLOW + Style.BRIGHT + "[WARN]   " + Style.RESET_ALL + "You have misinputted the file. Running play.py anyways...")

subprocess.run("python play.py", shell = True)