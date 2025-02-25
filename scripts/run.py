import os
import pickle
import yaml
import click
import chromadb

from ICRQE.workspace.summarize import summarize_file
from ICRQE.llm.llm_client import build_llm_completion_client, build_llm_chat_client
from ICRQE.storehouse.chromadb_utils import init_db, populate_db
from ICRQE.tools.tools_to_yaml import setup_and_load_yaml, setup_tools, save_tools_to_yaml
from ICRQE.agent.agent import Agent
from src.ICRQE.dataclasses_v1 import Config


@click.command()
@click.option('--config', '-c', default='config.yaml', help='Path to the config yaml file')
@click.option('--model', '-m', default='gpt-4-0125-preview', help='The name of the LLM model to use')
@click.option('--prompts_file', '-p', default=None, help='Path to the prompts file')
def main(config: str, model: str, prompts_file: str | None):
    """
    Main run script

    Args:
        config (str): Path to the config yaml file
        model (str): The name of the LLM model to use
        prompts_file (str | None): Path to the prompts file
    """

    # Load configuration
    with open(config, 'r') as f:
        config_data = yaml.safe_load(f)
    config = Config(**config_data)

    # Directory to store generated file and function descriptions
    os.makedirs(config.cache_dir, exist_ok=True)

    # Create the chromadb client
    client = chromadb.PersistentClient(config.db_path)

    # Initialize the database and get a list of files in the repo
    collection, files = init_db(client, os.path.expanduser(config.repository), config.extensions)
    files = sorted(files)

    # LLM that takes a string as input and returns a string
    llm = build_llm_completion_client(model)

    # File for storing LLM generated descriptions of files, functions, and classes
    descriptions_file = os.path.join(config.cache_dir, 'descriptions.pkl')

    # Load existing descriptions if available
    descriptions = {}
    if os.path.exists(descriptions_file):
        with open(descriptions_file, 'rb') as f:
            descriptions = pickle.load(f)

    # Generate summaries for files, classes, and functions
    for filepath in files:
        summarize_file(filepath, os.path.expanduser(config.repository), llm, descriptions)

    # Save the descriptions to a file in the cache directory
    with open(descriptions_file, 'wb') as f:
        pickle.dump(descriptions, f)

    # Populate the database with the descriptions
    populate_db(descriptions, collection)

    # Load or generate Tools
    tools_filepath = os.path.join(config.cache_dir, 'tools.yaml')
    tool_descriptions = setup_and_load_yaml(tools_filepath, 'tools')
    tools = setup_tools(
        config.Tools,
        tool_descriptions,
        collection,
        llm,
        os.path.expanduser(config.repository)
    )
    save_tools_to_yaml(tools, tools_filepath)

    # The agent LLM is a chat LLM that takes a list of messages as input and returns a message
    agent_chat_llm = build_llm_chat_client(model)
    agent = Agent(config, collection, agent_chat_llm, tools)
    agent.run()


if __name__ == '__main__':
    main()
