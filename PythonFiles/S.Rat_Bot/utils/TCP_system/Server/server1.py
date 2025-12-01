# TCP servers
import socket
import threading
import time
import os
import subprocess
import datetime
import sys
tcp_system_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(tcp_system_path)
from discordclient1 import DiscordBridge
from colorama import init, Fore, Style
from datetime import datetime, timedelta

# EDIT INACTIVITY TIME HERE
#                vvv
INACTIVITY_MINS = 3
last_activity = datetime.now()
inactivity_limit = timedelta(minutes=INACTIVITY_MINS)
activity_lock = threading.Lock()

def inactivity_watcher():
    while True:
        time.sleep(10)
        with activity_lock:
            if datetime.now() - last_activity > inactivity_limit:
                print(Fore.RED + "[AT;SHUTDOWN]" + Fore.RESET + f" No activity for the past {INACTIVITY_MINS} minutes. Shutting down server.")
                os._exit(0)

init(autoreset=True)

print_lock = threading.Lock()

HOST = '0.0.0.0' # <<< global
PORT = 12345

def handle_client(conn, addr):
    conn.settimeout(300)
    
    global last_activity
    with activity_lock:
        last_activity = datetime.now()
    print(Fore.YELLOW + "[TIMER RESET]" + Fore.RESET + " Client connected.")


    try:
        while True:
            try:
                data = conn.recv(1024)
                if not data:
                    with print_lock:
                        print(Fore.RED + "[DISCONNECT]" + Fore.RESET + f" A client was disconnected.")
                    with print_lock :
                        print("—" * 30)
                    break

                message = data.decode()
                with print_lock :
                    print(Fore.BLUE + "[INFO]" + Fore.RESET + f" [CLIENT] {message}")

                if message.strip() == "Send Client1DiscordMessage":
                    with print_lock :
                        print(Fore.BLUE + "[INFO]" + Fore.RESET + Style.BRIGHT + " Recieved Discord command signal.")

                    DiscordBridge.send_message("<:serverindc:1386697432334860340>testing")
                        # send a message activated from another file [discord command] 
                        # to here
                        # that sends to the same channel that the
                        # command is activated
                        #
                        # file path
                        # bot\
                        # |--TCP_system\
                        # |  |--discordclient.py
                        # |--Server\
                        # |  |--server1.py

                if message.strip() == "C205":
                    with print_lock :
                        print(Fore.RED + "[ML;SHUTDOWN]" + Fore.RESET + Style.BRIGHT + " Disconnection command received.")
                    os._exit(0)

            except socket.timeout:
                with print_lock :
                    print(Fore.RED + "[AT;SHUTDOWN]" + Fore.RESET + f" A client was inactive. Closing client connection.")
                break
            time.sleep(0.5)
    except Exception as e:
        with print_lock :
            print(Fore.RED + "[ERROR]" + Fore.RESET + f" {addr}: {e}")
    finally:
        conn.close()

def start_server():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((HOST, PORT))
    server_socket.listen()

    watcher_thread = threading.Thread(target=inactivity_watcher, daemon=True)
    watcher_thread.start()

    subprocess.run("cls", shell = True)

    print(Fore.GREEN + "[STARTING]" + Fore.RESET + f" Server is listening on {HOST}:{PORT}")
    print(Fore.BLUE + "[INFO]" + Fore.RESET + " : Inactivity watcher counts as a connection. +1 when a client is connected.")
    print(Fore.BLUE + "[INFO]" + Fore.RESET + " : Inactivity before disconnection time :" + Style.BRIGHT + f" {INACTIVITY_MINS} minutes")

    try:
        while True:
            conn, addr = server_socket.accept()

            client_thread = threading.Thread(target=handle_client, args=(conn, addr))
            client_thread.start()

            with print_lock:
                print(Fore.GREEN + "[ACTIVE CONNECTIONS]" + Fore.RESET + f" {threading.active_count() - 1}")

    except KeyboardInterrupt:
        print(Fore.RED + "[SHUTTING DOWN]" + Fore.RESET + "Server is closing.")
    finally:
        server_socket.close()

if __name__ == "__main__":
    start_server()
