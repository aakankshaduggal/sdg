import yaml

# parent class called block
class LLM_block:
    def __init__(self, config_path):
        """
        Initialize the LLM_block class with configuration.
        """
        # load json from config_path and get in config and loop through all keys
        self.block_config= load_config(config_path)
    
    def load_config(self, config_file):
        """
        Load the YAML configuration file.
        """
        with open(config_file, 'r') as file:
            config = yaml.safe_load(file)
        return config
    
    def _validate(self, sample):
        """
        Validate the sample with the  config.
        """
        # Placeholder for actual validation logic
        return True
    
    def generate(self, sample, client):
        """
        Generate samples using the client and configuration.
        """

         # Placeholder for actual generate logic
        if not self._validate(sample):
            # check type of sample
            # we expect a list of dictionaries
            raise ValueError("Sample validation failed.")
        
        generated_samples = []
        retries = 0

        # tackle cases for filtering
        # drop absolute duplicates
        
        while len(generated_samples) < self.num_samples and retries < self.max_retry:
            try:
                generated_sample = client.generate(sample, self.config_template)
                parsed_sample = self.parse(generated_sample)
                generated_samples.append(parsed_sample)
            except Exception as e:
                retries += 1
                if retries >= self.max_retry:
                    raise e
        
        return generated_samples
    
    def parse(self, content):
        """
        Parse the generated content based on start and end tags.
        """
         # Placeholder for actual parse logic
        start_index = content.find(self.start_tag) + len(self.start_tag)
        end_index = content.find(self.end_tag)
        return content[start_index:end_index]
