from instructlab.sdg import Pipeline

class SDG:

    def __init__(self, run_config, client):
        """
        Initialize the class with configuration.
        """
        # load json from config_path and get in config and loop through all keys
        self.sdg_config= load_config(config_path)
        self.client= client
        pipeline = Pipeline(self.sdg_config["pipeline_steps"])
        self.pipe = pipeline.create_pipeline()

    def generate(sample):
        """
        list of dictionaries
        """
        b_out = self.pipe[0].generate(sample)
        for block in self.pipe[1:]:
           # generate using the prompt template 
           b_out = block.generate(b_out)
        return b_out

    def load_config(self, config_file):
    """
    Load the YAML configuration file.
    Move to utils
    """
    with open(config_file, 'r') as file:
        config = yaml.safe_load(file)
    return config


