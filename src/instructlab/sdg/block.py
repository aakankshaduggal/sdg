import yaml

# parent class called block
class LLM_block:
    def __init__(self, config_path):
        """
        Initialize the Blocl class with configuration.
        """
        # load json from config_path and get in config and loop through all keys
        self.block_config= load_config(config_path)