# SPDX-License-Identifier: Apache-2.0

# Standard
from enum import Enum
from datetime import datetime
from pathlib import Path
from typing import Optional
import json
import os
import time

# Third Party
# instructlab - All of these need to go away (other than sdg) - issue #6
from datasets import concatenate_datasets, Dataset
import httpx
import openai

# First Party
# pylint: disable=ungrouped-imports
from instructlab.sdg import SDG, utils
from instructlab.sdg.default_flows import (
    DEFAULT_FLOW_FILE_MAP,
    MODEL_FAMILY_MERLINITE,
    MODEL_FAMILY_MIXTRAL,
    Flow,
)
from instructlab.sdg.pipeline import Pipeline
from instructlab.sdg.utils import models
from instructlab.sdg.utils.taxonomy import (
    leaf_node_to_samples,
    read_taxonomy_leaf_nodes,
)
from instructlab.sdg.utils.parse_and_convert import (
    _unescape,
    _convert_to_messages,
    _convert_to_hack_fmt,
)
from instructlab.sdg.utils.datamixing import (
    Recipe,
)
from instructlab.sdg.logger_config import setup_logger

# Constants
logger = setup_logger(__name__)
NUM_SYNTH_SKILLS = 30


def _sdg_init(pipeline, client, num_instructions_to_generate):
    knowledge_flows = []
    freeform_skill_flows = []
    grounded_skill_flows = []

    if pipeline == "full":
        knowledge_flows.append(
            Flow(client).get_flow_from_file(DEFAULT_FLOW_FILE_MAP["MMLUBenchFlow"])
        )
        knowledge_flows.append(
            Flow(client).get_flow_from_file(DEFAULT_FLOW_FILE_MAP["SynthKnowledgeFlow"])
        )
        freeform_skill_flows.append(
            Flow(client, num_instructions_to_generate).get_flow_from_file(
                DEFAULT_FLOW_FILE_MAP["SynthSkillsFlow"]
            )
        )
        grounded_skill_flows.append(
            Flow(client, num_instructions_to_generate).get_flow_from_file(
                DEFAULT_FLOW_FILE_MAP["SynthGroundedSkillsFlow"]
            )
        )
    elif pipeline == "simple":
        knowledge_flows.append(
            Flow(client).get_flow_from_file(
                DEFAULT_FLOW_FILE_MAP["SimpleKnowledgeFlow"]
            )
        )
        freeform_skill_flows.append(
            Flow(client, num_instructions_to_generate).get_flow_from_file(
                DEFAULT_FLOW_FILE_MAP["SimpleFreeformSkillFlow"]
            )
        )
        grounded_skill_flows.append(
            Flow(client, num_instructions_to_generate).get_flow_from_file(
                DEFAULT_FLOW_FILE_MAP["SimpleGroundedSkillFlow"]
            )
        )
    elif os.path.isfile(pipeline):
        flow = Flow(client, num_instructions_to_generate).get_flow_from_file(pipeline)
        knowledge_flows = [flow]
        freeform_skill_flows = [flow]
        grounded_skill_flows = [flow]
    else:
        raise utils.GenerateException(f"Error: pipeline ({pipeline}) is not supported.")

    sdg_knowledge = SDG([Pipeline(flow) for flow in knowledge_flows])
    sdg_freeform_skill = SDG([Pipeline(flow) for flow in freeform_skill_flows])
    sdg_grounded_skill = SDG([Pipeline(flow) for flow in grounded_skill_flows])
    return sdg_knowledge, sdg_freeform_skill, sdg_grounded_skill


def get_taxonomy_data(
    leaf_nodes,
    sys_prompt,
):
    taxonomy_data = []
    for _, leaf_node in leaf_nodes.items():
        for seed_example in leaf_node:
            user = seed_example["instruction"]  # question

            if len(seed_example["input"]) > 0:
                user += "\n" + seed_example["input"]  # context

            taxonomy_data.append(
                {
                    "system": sys_prompt,
                    "user": _unescape(user),
                    "assistant": _unescape(seed_example["output"]),  # answer
                }
            )
    taxonomy_ds = Dataset.from_list(taxonomy_data)
    return taxonomy_ds


# TODO - parameter removal needs to be done in sync with a CLI change.
# pylint: disable=unused-argument
def generate_data(
    logger,
    api_base,
    api_key: Optional[str] = None,
    model_family: Optional[str] = None,
    model_name: Optional[str] = None,
    # TODO - not used -- when batching is enabled, this is relevant.
    # Right now the code hard codes 8 cpus for batching
    num_cpus: Optional[int] = None,
    num_instructions_to_generate: Optional[int] = 30,
    taxonomy: Optional[str] = None,
    taxonomy_base: Optional[str] = None,
    output_dir: Optional[str] = None,
    # TODO - not used and should be removed from the CLI
    prompt_file_path: Optional[str] = None,
    # TODO - probably should be removed
    rouge_threshold: Optional[float] = None,
    console_output=True,
    yaml_rules: Optional[str] = None,
    chunk_word_count=None,
    server_ctx_size=None,
    tls_insecure=False,
    tls_client_cert: Optional[str] = None,
    tls_client_key: Optional[str] = None,
    tls_client_passwd: Optional[str] = None,
    # TODO need to update the CLI to specify which pipeline to use (simple or full at the moment)
    pipeline: Optional[str] = "simple",
):
    logger = setup_logger(__name__)
    generate_start = time.time()

    knowledge_recipe = Recipe("/shiv/sdg-ad/src/instructlab/sdg/configs/knowledge/data_recipe/default_recipe.yaml")
    skills_recipe = Recipe("/shiv/sdg-ad/src/instructlab/sdg/configs/skills/data_recipe/default_recipe.yaml")

    sys_prompt = knowledge_recipe.sys_prompt    
    logger.info(f"System prompt: {sys_prompt}")
    assert sys_prompt == skills_recipe.sys_prompt, "System prompts must be the same for both knowledge and skills"

    if not os.path.exists(output_dir):
        os.mkdir(output_dir)

    if not (taxonomy and os.path.exists(taxonomy)):
        raise utils.GenerateException(f"Error: taxonomy ({taxonomy}) does not exist.")

    leaf_nodes = read_taxonomy_leaf_nodes(taxonomy, taxonomy_base, yaml_rules)
    logger.info(f"Found {len(leaf_nodes)} leaf nodes in the taxonomy.")
    logger.info(f"Generating data for {list(leaf_nodes.keys())} leaf nodes.")

    if not leaf_nodes:
        raise utils.GenerateException("Error: No new leaf nodes found in the taxonomy.")

    name = Path(model_name).stem  # Just in case it is a file path
    date_suffix = datetime.now().replace(microsecond=0).isoformat().replace(":", "_")
    output_file_train = f"train_{name}_{date_suffix}.jsonl"

    # this file needs to be revisted later - retaining for now
    output_file_test = f"test_{name}_{date_suffix}.jsonl"
    
    taxonomy_ds = get_taxonomy_data(leaf_nodes, sys_prompt=sys_prompt)
    logger.info(f"Generating to: {os.path.join(output_dir, output_file_test)}")
    taxonomy_ds.to_json(os.path.join(output_dir, output_file_test))

    orig_cert = (tls_client_cert, tls_client_key, tls_client_passwd)
    cert = tuple(item for item in orig_cert if item)
    verify = not tls_insecure
    client = openai.OpenAI(
        base_url=api_base,
        api_key=api_key,
        http_client=httpx.Client(cert=cert, verify=verify),
    )

    if models.get_model_family(model_family, model_name) == "mixtral":
        model_family = MODEL_FAMILY_MIXTRAL
    else:
        model_family = MODEL_FAMILY_MERLINITE

    # TODO -- llama-cpp doesn't support batching, we need to get a hint from the CLI
    # about whether we can turn this on (whether vllm is used or not)

    sdg_knowledge, sdg_freeform_skill, sdg_grounded_skill = _sdg_init(
        pipeline,
        client,
        num_instructions_to_generate,
    )

    if console_output:
        logger.info(
            "Synthesizing new instructions. If you aren't satisfied with the generated instructions, interrupt training (Ctrl-C) and try adjusting your YAML files. Adding more examples may help."
        )

    is_knowledge = False

    for i, leaf_node in enumerate(leaf_nodes.values()):
        samples = leaf_node_to_samples(leaf_node, server_ctx_size, chunk_word_count)
        ds = Dataset.from_list(samples)

        if not samples:
            raise utils.GenerateException("Error: No samples found in leaf node.")

        if samples[0].get("document"):
            sdg = sdg_knowledge
            logger.info(f"Generating data for leaf node {i} with knowledge pipeline.")
            is_knowledge = True
            # add to 0.7 recipe
            # add to 1.0 recipe

        elif samples[0].get("context"):
            sdg = sdg_grounded_skill
            logger.info(f"Generating data for leaf node {i} with grounded skill pipeline.")
            # add to 1.0 recipe

        else:
            sdg = sdg_freeform_skill
            logger.info(f"Generating data for leaf node {i} with freeform skill pipeline.")
            # add to 1.0 recipe
        

        generated_data = sdg.generate(ds)

        if is_knowledge:
            # pretraining_data = generated_data.map(...)
            # qa_data_in_skills = generate_data.map(...)

            # pretraining_data.to_json(...)
            # qa_data_in_skills.to_json(...)

            # knowledge_recipe.add_dataset(...)
            # skills_recipe.add_dataset(...)
            pass
        
        else:
            messages = generated_data.map(
                _convert_to_messages,
                fn_kwargs={"sys_prompt": sys_prompt},
                num_proc=8,
            )

            fpath = os.path.join(output_dir, f"node_datasets_{date_suffix}/node_{i}.jsonl")
            messages.to_json(fpath, orient="records", lines=True)
            skills_recipe.add_dataset(fpath, NUM_SYNTH_SKILLS)
    

    if knowledge_recipe.dataset_added:
        knowledge_recipe.save_recipe(f"{output_dir}/knowledge_recipe_{date_suffix}.yaml")
        knowledge_recipe.save_mixed_dataset(f"{output_dir}/knowledge_train_msgs_{date_suffix}.jsonl")
                                                                                 
    if skills_recipe.dataset_added:
        skills_recipe.save_recipe(f"{output_dir}/skills_recipe_{date_suffix}.yaml")
        skills_recipe.save_mixed_dataset(f"{output_dir}/skills_train_msgs_{date_suffix}.jsonl")

    logger.info(f"Generation complete in {time.time() - generate_start:.2f}s")
