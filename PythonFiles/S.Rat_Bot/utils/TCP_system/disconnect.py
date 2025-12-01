# dcserv.py
import socket
from colorama import init, Fore, Style
import os
from dotenv import load_dotenv
load_dotenv()

serv_ip=os.getenv("SERVER_IP")

init(autoreset=True)

HOST = f'{serv_ip}'
PORT = 65536

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.connect((HOST, PORT))
    s.sendall(b"ML;DC")

print(Fore.RED + "Disconnect command recieved.")
print(Fore.RED + "Server now disconnecting.")
