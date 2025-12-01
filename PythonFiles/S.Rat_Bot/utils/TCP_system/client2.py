# client.py
import socket
import time
from colorama import init, Fore, Style
import os
from dotenv import load_dotenv
load_dotenv()

serv_ip = os.getenv("SERVER_IP")
port = 12345

print(Style.BRIGHT + Fore.YELLOW + "[WARN]" + Style.RESET_ALL + Fore.RESET + " : This file is on testing.")
print(Style.BRIGHT + Fore.BLUE + "[INFO]" + Style.RESET_ALL + Fore.RESET + " : You are running Client2.")

client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client_socket.connect((f'{serv_ip}', port))

message = ["Client2 message fetched successfully!"]
for msg in message:
    client_socket.sendall(msg.encode())
    time.sleep(2)

client_socket.close()

print(Style.BRIGHT + Fore.BLUE + "[INFO]" + Style.RESET_ALL + Fore.RESET + " : Ran Client2 successfully.")
