class Generate:
    def __init__(self, example, num_samples, pipeline):
        """
        Initialize the Generate class with an example, the number of examples to generate, 
        and a pipeline object.
        """
        self.example = example
        self.num_samples = num_samples
    
    def gen_samples(self):
        """
        Generate a specified number of examples using the pipeline object.
        """
        gen_samples = []
        for _ in range(self.num_samples):
            generated_example = self.pipeline.process(self.example)
            gen_samples.append(generated_example)
        return gen_samples
