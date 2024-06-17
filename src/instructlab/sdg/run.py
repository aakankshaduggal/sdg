from sdg import Pipeline

# Initialize Pipeline class with the configuration file
pipeline = Pipeline(config_file='path/to/configs/v1_config.json')

# Example input data
example_data = 'example_data'

# Process the example data through the pipeline
generated_examples = pipeline.process(example_data)

# Print generated examples
print(generated_examples)
