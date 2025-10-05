import random
import time
import os

# ANSI escape code for amber color (a shade of yellow/orange)
AMBER_COLOR = "\033[38;5;214m"  # Amber color
RESET_COLOR = "\033[0m"

# List of malicious-sounding computery phrases
computery_things = [
    "Accessing restricted files...",
    "Disabling firewall protections...",
    "Injecting malicious payload...",
    "Overriding access controls...",
    "Decrypting secure archives...",
    "Executing unauthorized command...",
    "Interfacing with remote server...",
    "Scraping sensitive information...",
    "Erasing audit logs...",
    "Spoofing IP addresses...",
    "Compromising system integrity...",
    "Injecting rootkits into memory...",
    "Uploading ransomware...",
    "Bypassing encryption protocols...",
    "Hijacking system processes...",
    "Corrupting data clusters...",
    "Obfuscating traces...",
    "Scanning for vulnerabilities...",
    "Infiltrating database...",
    "Escalating privileges...",
    "Manipulating network traffic...",
    "Modifying system kernel...",
    "Capturing keyboard input...",
    "Rewriting security protocols...",
    "Installing backdoor entry...",
    "Executing brute-force attack...",
    "Interfering with resource allocation...",
    "Redirecting network packets...",
    "Disguising malicious code...",
    "Exfiltrating data to unknown IP...",
    "Engaging DDoS protocols...",
    "Accessing critical systems...",
    "Injecting false system alerts...",
]

# Function to randomly clear the screen
def random_screen_wipe():
    os.system('cls' if os.name == 'nt' else 'clear')

# Function to print random malicious phrases with ellipses in amber
def generate_random_malicious_phrases():
    while True:
        # Randomly clear the screen every 5-10 lines
        if random.randint(1, 10) > 8:
            random_screen_wipe()

        phrase = random.choice(computery_things)
        print(f"{AMBER_COLOR}{phrase}", end="", flush=True)
        time.sleep(0.5)  # Pause for dramatic effect
        print("...", RESET_COLOR)
        time.sleep(1)  # Adjust delay if needed

# Run the function
generate_random_malicious_phrases()
