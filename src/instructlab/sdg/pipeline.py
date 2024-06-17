import json
import os
from instructlab.sdg.LLM_block import LLM_block

class Pipeline:
    def __init__(self, config_file):
        """
        Initialize the Pipeline class with a configuration file.
        """
        self.pipeline_config_file = self.load_config(config_file)
        self.steps = self.create_pipeline()
    
    def create_pipeline(self):
        """
        Create a pipeline based on the specified version's config file.
        """
        # call steps blocks instead
        # config = self.load_config(self.config_file)
        steps = []
        for step_name, step_config in self.config.get("pipeline_steps", {}).items():
            steps.append(LLM_block(step_config))
        return steps
    
    def load_config(self, config_file):
        """
        Load the configuration from the specified config file.
        """
        with open(config_file, 'r') as file:
            config = json.load(file)
        return config
