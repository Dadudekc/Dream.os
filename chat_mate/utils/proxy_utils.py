import random

PROXY_LIST = [
    "http://username:password@proxy1.example.com:port",
    "http://username:password@proxy2.example.com:port",
    # Add more proxies
]

def get_random_proxy():
    return random.choice(PROXY_LIST) if PROXY_LIST else None
