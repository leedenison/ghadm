# ghadm
GitHub Admin CLI Tool

## Install

```bash
$ git clone https://github.com/leedenison/ghadm.git
$ pip install ghadm/
```

## Usage

```
usage: ghadm label [-h] {sync,search,delete} ...

positional arguments:
  {sync,search,delete}
    sync                sync labels for a GitHub organization
    search              search for labels in a GitHub organization
    delete              delete a label from a GitHub organization

options:
  -h, --help            show this help message and exit
```

## Configuration

```
$ cat ~/.ghadm.yaml

endpoint: https://api.github.com/graphql 
access_token: <YOUR_ACCESS_TOKEN>

organization: leedenison
project_repos:
    - ghadm
labels:
    "bug":
      description: "bug or defect"
      color: "B60205"
    "feature: rickrolling":
      description: "work items relating to the rickrolling feature"
      color: "C2E0C6"
    "code health":
      description: ""
      color: "C5DEF5"
    "technical debt":
      description: ""
      color: "C5DEF5"
      synonyms:
        - "tech debt"
        - "clean up"
```

