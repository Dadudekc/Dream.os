    def __init__(self, tabs: dict):
        self.tabs = tabs
        self.error_messages = [] # Initialize the missing attribute

    def validate(self):
        for name, tab_instance in self.tabs.items(): 