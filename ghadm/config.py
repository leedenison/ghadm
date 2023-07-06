import yaml
import os

def ReadConfig() -> dict:
    try:
        with open(os.path.expanduser('~') + "/.ghadm.yaml", "r") as stream:
            config = yaml.safe_load(stream)
            return config
    except yaml.YAMLError as exc:
        print("Failed to parse config file:")
        print(exc)
        return None
    except OSError as exc:
        print("Failed to read config file:")
        PrintUsage()
        return None


def PrintUsage():
    print("Please create a file ~/.ghadm.yaml and ensure it is readable, eg:")
    print("")
    print("access_token: <YOUR ACCESS TOKEN>")
    print("organisation: Hypothesis")
    print("project_repos:")
    print("    - h")
    print("    - product-backlog")
    print("labels:")
    print("    \"bug\":")
    print("        description: \"\"")
    print("        color: \"B60205\"")
