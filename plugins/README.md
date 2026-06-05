# Phoenix Plugin System

Drop any `.py` file into this `plugins/` folder and Phoenix will load it automatically on startup.

## Plugin structure

Every plugin needs exactly two things:

```python
COMMAND     = "weather"          # the slash command (no slash)
DESCRIPTION = "Get local weather info"
USAGE       = "/weather London"  # shown in /plugins list

def run(args: str, session_id: str = None) -> str:
    """Return a plain-text reply string."""
    ...
```

## Built-in plugins

| Command | Description |
|:--------|:------------|
| `/remind` | Set a simple reminder |
| `/joke` | Get a random joke |
| `/calc` | Evaluate a math expression |

## Example

```python
# plugins/greet.py
COMMAND     = "greet"
DESCRIPTION = "Greet someone by name"
USAGE       = "/greet <name>"

def run(args: str, session_id: str = None) -> str:
    name = args.strip() or "friend"
    return f"Hey {name}! 👋 Great to meet you."
```

Then in Phoenix:
```
You: /greet Alex
Phoenix: Hey Alex! 👋 Great to meet you.
```

## Rules

- Return a plain string — Phoenix will display it directly.
- `session_id` is passed in case you need to read/write user memory.
- Any exception you raise is caught and shown as an error message.
- Plugins are reloaded only on server restart.
