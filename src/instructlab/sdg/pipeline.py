import json
import os
from .step import Step

class Pipeline:
    def __init__(self, config_file):
        """
        Initialize the Pipeline class with a configuration file.
        """
        self.config_file = config_file
        self.steps = self.create_pipeline()
    
    def create_pipeline(self):
        """
        Create a pipeline based on the specified version's config file.
        """
        config = self.load_config(self.config_file)
        steps = []
        for step_name, step_config in config.get("pipeline_steps", {}).items():
            steps.append(Step(step_name, step_config))
        return steps
    
    def load_config(self, config_file):
        """
        Load the configuration from the specified config file.
        """
        with open(config_file, 'r') as file:
            config = json.load(file)
        return config
    
    def process(self, example):
        """
        Process an example through the pipeline steps.
        """
        processed_example = example
        for step in self.steps:
            processed_example = step.generate(processed_example)
        return processed_example
