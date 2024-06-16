###########################################
#             ODUS - OnajLikezz
#       https://github.com/onajlikezz     
#       https://discord.gg/pBFaCQQVBV
#       https://youtube.com/onajlikezz
###########################################
try:
    import random
    import requests
    import json
    import time
    import os
    from colorama import Fore, init
except:
    os.system("pip install random")
    os.system("pip install requests")
    os.system("pip install json")
    os.system("pip install time")
    os.system("pip install colorama")

def cls():
    if os.name == 'nt':  # For Windows
        os.system('cls')
    else:  # For Unix/Linux/Mac
        os.system('clear')
cls()
os.system("title Onaj Discord Username Sniper")
ASCI = """
             ██████╗ ██████╗ ██╗   ██╗███████╗
            ██╔═══██╗██╔══██╗██║   ██║██╔════╝
            ██║   ██║██║  ██║██║   ██║███████╗
            ██║   ██║██║  ██║██║   ██║╚════██║
            ╚██████╔╝██████╔╝╚██████╔╝███████║
             ╚═════╝ ╚═════╝  ╚═════╝ ╚══════╝                                                                                                                                                                                                                                      
"""
print(ASCI)
######## --> CONFIG
delay = float(input("Delay?:"))
char = float(input("Char?:"))
webhook_url = input("Webhook:")
#
cls()
print(ASCI)
while True:
    time.sleep(delay)
    # Inicijalizacija boja
    init(autoreset=True)

    def generate_random_username():
        chars = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_.'
        return ''.join(random.choice(chars) for _ in range(int(char)))

    def check_username_availability(webhook_url):
        url = "https://discord.com/api/v9/auth/register"

        random_username = generate_random_username()

        payload = {
            "email": "onajlikezz@onajx.coom",
            "username": random_username,
            "global_name": "onajlikezz",
            "password": "onajlikezz",
            "invite": None,
            "consent": True,
            "date_of_birth": "2002-05-06",
        }

        headers = {
            "Content-Type": "application/json"
        }

        response = requests.post(url, data=json.dumps(payload), headers=headers)
        response_data = response.json()

        if response_data.get('message') == "Invalid Form Body" and response_data.get('code') == 50035:
            username_errors = response_data['errors']['username']['_errors']
            for error in username_errors:
                if error['code'] == "USERNAME_ALREADY_TAKEN":
                    print(Fore.RED + f"                      {random_username} is Taken!")
                    return

        print(Fore.BLUE + f"                    {random_username} is available!")

        # Slanje poruke na Discord webhook
        webhook_payload = {
            "embeds": [{
                "title": "Username Availability",
                "description": f"`{random_username}` is available!",
                "color": 3066993  # Zelena boja za embed
        }]
        }
        requests.post(webhook_url, data=json.dumps(webhook_payload), headers=headers)

    if __name__ == "__main__":
        check_username_availability(webhook_url)
