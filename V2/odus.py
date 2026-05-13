###########################################
#             ODUS - OnajLikezz
#       https://github.com/onajlikezz
#       https://discord.gg/pBFaCQQVBV
#       https://youtube.com/onajlikezz
###########################################
import random
import requests
import json
import time
import os
import webbrowser
import shutil
from colorama import Fore, Style, init

init(autoreset=True)

def cls():
    os.system('cls' if os.name == 'nt' else 'clear')

def center_text(text):
    """Centrira tekst prema širini terminala."""
    try:
        width = shutil.get_terminal_size().columns
    except:
        width = 80
    lines = text.split('\n')
    centered = []
    for line in lines:
        if len(line) >= width:
            centered.append(line)
        else:
            pad = (width - len(line)) // 2
            centered.append(' ' * pad + line)
    return '\n'.join(centered)

def cprint(text, color=''):
    """Štampa centrirani tekst sa opcionom bojom."""
    if color:
        print(color + center_text(text) + Style.RESET_ALL)
    else:
        print(center_text(text))

def show_links():
    cprint("     Discord: " + Fore.BLUE + "discord.gg/yXeWQ6arcq", Fore.CYAN)
    cprint("     GitHub:  " + Fore.BLUE + "github.com/onajlikezz", Fore.CYAN)
    cprint("Press [D] for Discord, [G] for GitHub, [ENTER] to continue...", Fore.YELLOW)

def main():
    cls()
    ASCI = """
            ███████    ██████████   █████  █████  █████████ 
          ███▒▒▒▒▒███ ▒▒███▒▒▒▒███ ▒▒███  ▒▒███  ███▒▒▒▒▒███
         ███     ▒▒███ ▒███   ▒▒███ ▒███   ▒███ ▒███    ▒▒▒ 
        ▒███      ▒███ ▒███    ▒███ ▒███   ▒███ ▒▒█████████ 
        ▒███      ▒███ ▒███    ▒███ ▒███   ▒███  ▒▒▒▒▒▒▒▒███
        ▒▒███     ███  ▒███    ███  ▒███   ▒███  ███    ▒███
         ▒▒▒███████▒   ██████████   ▒▒████████  ▒▒█████████ 
           ▒▒▒▒▒▒▒    ▒▒▒▒▒▒▒▒▒▒     ▒▒▒▒▒▒▒▒    ▒▒▒▒▒▒▒▒▒  
                                                            2.0 - OnajLikezz                                                            
    """
    cprint(ASCI, Fore.MAGENTA)
    cprint("Onaj Discord Username Sniper v2.0", Fore.GREEN)
    print()
    show_links()

    while True:
        try:
            choice = input().strip().lower()
        except EOFError:
            break
        if choice == 'd':
            webbrowser.open("https://discord.gg/yXeWQ6arcq")
            show_links()
        elif choice == 'g':
            webbrowser.open("https://github.com/onajlikezz")
            show_links()
        elif choice == '':
            break
        else:
            cprint("Unknown option, try again.", Fore.RED)

    cls()
    cprint(ASCI, Fore.MAGENTA)

    # Konfiguracija
    try:
        delay = float(input(center_text(Fore.YELLOW + "Delay (seconds): " + Fore.WHITE) + '\n'))
        char = int(input(center_text(Fore.YELLOW + "Username length (characters): " + Fore.WHITE) + '\n'))
        webhook_url = input(center_text(Fore.YELLOW + "Discord webhook URL (for notifications): " + Fore.WHITE) + '\n')
    except ValueError:
        cprint("Invalid input. Using default values.", Fore.RED)
        delay = 1.0
        char = 5
        webhook_url = ""

    cls()
    cprint(ASCI, Fore.MAGENTA)
    cprint(f"Sniping started | Delay: {delay}s | Length: {char} chars", Fore.GREEN)
    cprint("Press CTRL+C to stop.", Fore.CYAN)
    print()

    total_checked = 0
    total_available = 0

    try:
        while True:
            time.sleep(delay)
            total_checked += 1

            chars = 'abcdefghijklmnopqrstuvwxyz0123456789_.'
            username = ''.join(random.choice(chars) for _ in range(char))

            url = "https://discord.com/api/v9/unique-username/username-attempt-unauthed"
            headers = {"Content-Type": "application/json"}
            payload = {"username": username}

            try:
                resp = requests.post(url, json=payload, headers=headers, timeout=10)
                if resp.status_code != 200:
                    cprint(f"[{total_checked}] {username} - API error ({resp.status_code})", Fore.RED)
                    continue
                data = resp.json()
            except Exception as e:
                cprint(f"[{total_checked}] {username} - Error: {e}", Fore.RED)
                continue

            if data.get("taken", True):
                line = f"[{total_checked}] {username} is TAKEN"
                cprint(line, Fore.RED)
            else:
                line = f"[{total_checked}] {username} is AVAILABLE !!!"
                total_available += 1
                cprint(line, Fore.GREEN)

                if webhook_url:
                    hook_data = {
                        "embeds": [{
                            "title": "Username Available!",
                            "description": f"`{username}` is free to claim.",
                            "color": 3066993,
                            "footer": {"text": "ODUS Sniper by OnajLikezz"}
                        }]
                    }
                    try:
                        requests.post(webhook_url, json=hook_data, headers=headers, timeout=10)
                    except:
                        cprint("Webhook notification failed.", Fore.YELLOW)

    except KeyboardInterrupt:
        cprint("\n\nSniping stopped.", Fore.YELLOW)
        cprint(f"Total checked: {total_checked}", Fore.CYAN)
        cprint(f"Available found: {total_available}", Fore.CYAN)
        try:
            input(center_text("Press Enter to exit...") + '\n')
        except (EOFError, KeyboardInterrupt):
            pass
        finally:
            os._exit(0)

if __name__ == "__main__":
    main()