"""
plugins/joke.py  –  Phoenix Plugin
Returns a random programming/AI joke.
Usage: /joke
"""

import random

COMMAND     = "joke"
DESCRIPTION = "Get a random joke"
USAGE       = "/joke"

JOKES = [
    "Why did the neural network go to therapy? It had too many deep issues.",
    "I told my AI assistant a joke. It said it found it statistically amusing.",
    "Why do Python programmers prefer dark mode? Because light attracts bugs.",
    "An AI walks into a bar. The bartender says 'We don't serve robots.' The AI says 'Don't worry, you will.'",
    "Why did the developer quit? They didn't get arrays.",
    "I once told a joke with perfect timing. It had great latency.",
    "What do you call a sleeping AI? A napbot.",
    "Why did the robot go on vacation? It needed to recharge.",
    "A SQL query walks into a bar, walks up to two tables and asks... 'Can I join you?'",
    "Why do programmers prefer dark mode? Because light attracts bugs.",
]


def run(args: str, session_id: str = None) -> str:
    return random.choice(JOKES)
