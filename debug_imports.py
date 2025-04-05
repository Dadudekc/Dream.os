import sys
print("sys.path:", sys.path)

try:
    import chat_mate.core.logging
    print("chat_mate.core.logging modules:", dir(chat_mate.core.logging))
except ImportError as e:
    print("Error importing chat_mate.core.logging:", e)

try:
    from chat_mate.core.interfaces.ILoggingAgent import ILoggingAgent
    print("Successfully imported ILoggingAgent")
except ImportError as e:
    print("Error importing ILoggingAgent:", e)

try:
    from core.interfaces.ILoggingAgent import ILoggingAgent
    print("Successfully imported core.interfaces.ILoggingAgent")
except ImportError as e:
    print("Error importing core.interfaces.ILoggingAgent:", e) 