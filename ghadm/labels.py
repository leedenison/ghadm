import sys
import math
import re
from ghadm.client import Client, Repository, Label

GREEN = '\033[92m'
RED = '\033[91m'
END = '\033[0m'

DELETE_LINE = '\033[2K\r'

class ActionUnimplemented(Exception):
    pass


class Action:
    def __init__(
            self,
            action: str,
            org: str,
            repo: Repository,
            extant: Label,
            update: Label):
        self.action = action
        self.org = org
        self.repo = repo
        self.extant = extant
        self.update = update

    def __repr__(self):
        return 'Action<{}, {}, {}, {}, {}>'.format(
            repr(self.action),
            repr(self.org),
            repr(self.repo),
            repr(self.extant),
            repr(self.update)) 

    def __eq__(self, other): 
        if not isinstance(other, Action):
            return False

        return (self.action == other.action and
                self.org == other.org and
                self.repo == other.repo and
                self.extant == other.extant and
                self.update == other.update)

    def FormattedString(self, show_issue_count: bool) -> str:
        """ Returns a formatted string describing the action. """
        output = (self.action + ':').ljust(10)

        if show_issue_count:
            affected = 0
            if self.extant:
                affected = len(self.repo.IssuesByLabel(self.extant.id))
            output += ('[' + str(affected) + ']').ljust(6)
          
        output += self.org + '/' + str(self.repo.name)

        update = '('
        if self.extant and self.update.name != self.extant.name:
            update += '"' + str(self.extant.name) + '" -> '
        update += '"' + str(self.update.name) + '"'

        if self.extant and self.update.color != self.extant.color:
            update += ', "' + str(self.extant.color) + '" -> '
            update += '"' + str(self.update.color) + '"'

        if self.extant and self.update.description != self.extant.description:
            update += ', "' + str(self.extant.description) + '" -> '
            update += '"' + str(self.update.description) + '"'
        update += ')'

        return output + update


    def Execute(self, client: Client):
        """ Executes the action. """
        if self.action == 'create':
            client.CreateLabel(self.repo, self.update)
        elif self.action == 'edit':
            client.EditLabel(self.extant, self.update)
        elif self.action == 'relabel':
            issues = self.repo.IssuesByLabel(self.extant.id)
            client.Relabel(issues, self.extant, self.update)
        else:
            raise ActionUnimplemented()


def Sync(client: Client, config: dict, relabel: bool):
    """ Syncs labels for all configured repos.

        First prints a list of actions that will be executed, then prompts for
        confirmation before executing the actions.

        Args:
          client: A Client used to connect to the GitHub API.
          config: A dict containing the configuration for the GitHub organization.
          relabel: Flag indicating whether to merge synonyms and relabel issues.
    """
    repos = {}
    for repo in config['project_repos']:
        print('Fetching data for repository: ', end='')
        print('{}/{}...'.format(config['organization'], repo), end='')
        sys.stdout.flush()
        repos[repo] = client.Repository(config['organization'], repo, relabel)
        print(DELETE_LINE, end='')

    actions = []
    for repo in repos:
        actions += GenerateSyncActions(config, repos[repo])

    print('The following label actions will be executed:')
    if relabel:
        print('  <action>: [# issues] (label edits)')
    else:
        print('  <action>: (label edits)')
    max_length = 0
    for a in actions:
        action_string = a.FormattedString(show_issue_count=relabel)
        if len(action_string) > max_length:
            max_length = len(action_string)
        print('  ' + action_string, end='\n')

    print('\nConfirm {} label actions: [y/N]: '.format(str(len(actions))), end='')

    i = input().lower()

    if i == 'y' or i == 'yes':
        try:
            for a in actions:
                action_string = a.FormattedString(show_issue_count=relabel)
                print('  ' + action_string.ljust(max_length + 2), end='')

                if not relabel and a.action == 'relabel':
                    print('['+RED+'SKIPPED'+END+']')
                    continue
                else:
                    a.Execute(client)
                    print('['+GREEN+'OK'+END+']')
        except Exception as e:
            print('['+RED+'FAILED'+END+']')
            traceback.print_exc()


def GenerateSyncActions(config: dict, repo: Repository) -> list[Action]:
    """ Generates a list of actions to sync the labels for a repo.

        Args:
          config: A dict containing the configuration for the GitHub organization.
          repo: A Repository object for the repo to sync.
    """
    actions = []
    labels_map = repo.LabelsByLowerName()
    
    # Create actions for configured labels
    for cfg_name in config['labels']:
        cfg_label = config['labels'][cfg_name]
        lc_cfg_name = cfg_name.lower()

        if lc_cfg_name in labels_map:
            # Label already exists.
            # Check if anything needs to be updated for the label.
            if (cfg_name != labels_map[lc_cfg_name].name
                or cfg_label['color'] != labels_map[lc_cfg_name].color
                or cfg_label['description'] != labels_map[lc_cfg_name].description):
                actions.append(
                    Action(
                        'edit',
                        config['organization'],
                        repo,
                        labels_map[lc_cfg_name],
                        Label(
                            labels_map[lc_cfg_name].id,
                            cfg_name,
                            cfg_label['description'],
                            cfg_label['color'])))
        else:
            # Label does not exist.
            # Create label.
            actions.append(
                Action(
                    'create',
                    config['organization'],
                    repo,
                    None,
                    Label(
                        None,
                        cfg_name,
                        cfg_label['description'],
                        cfg_label['color'])))

        # Create actions for configured synonyms
        if 'synonyms' in cfg_label:
            for synonym in cfg_label['synonyms']:
                lc_synonym = synonym.lower()

                if lc_synonym in labels_map:
                    # Collapse a relabel action with a corresponding create to an
                    # edit action
                    action = 'relabel'
                    idx = findAction(actions, 'create', cfg_name)
                    if idx >= 0:
                        action = 'edit'
                        del actions[idx]

                    actions.append(
                        Action(
                            action,
                            config['organization'],
                            repo,
                            labels_map[lc_synonym],
                            Label(
                                labels_map[lc_cfg_name].id,
                                cfg_name,
                                cfg_label['description'],
                                cfg_label['color'])))

    return actions


def DeleteLabel(client: Client, config: dict, label: str):
    """ Deletes a label from all configured repos.

        Args:
          client: A Client used to connect to the GitHub API.
          config: A dict containing the configuration for the GitHub organization.
          label: The name of the label to delete.
    """
    repos = {}
    for repo in config['project_repos']:
        print('Fetching data for repository: ', end='')
        print('{}/{}...'.format(config['organization'], repo), end='')
        sys.stdout.flush()
        repos[repo] = client.Repository(config['organization'], repo, fetch_issues=False)
        print(DELETE_LINE, end='')

    labels = {}
    for repo in repos:
        labels_by_lower = repos[repo].LabelsByLowerName()
        if label.lower() in labels_by_lower:
            labels[repo] = labels_by_lower[label.lower()]

    print('Label "{}" will be deleted from the following repositories:'.format(label))
    for repo in labels:
        print('  {}/{}'.format(config['organization'], repo))

    print('\nConfirm deletion from {} repositories: [y/N]: '.format(
        str(len(labels))), end='')

    i = input().lower()

    if i == 'y' or i == 'yes':
        for repo in labels:
            try:
                print('Deleting "{}" from {}/{}'.format(
                    label, config['organization'], repo).ljust(50), end='')
                sys.stdout.flush()
                client.DeleteLabel(labels[repo])
                print('['+GREEN+'OK'+END+']')
            except Exception as e:
                print('['+RED+'FAILED'+END+']')
                traceback.print_exc()


def SearchLabel(client: Client, config: dict, pattern: str):
    """ Searches for a label in all configured repos.

        Args:
          client: A Client used to connect to the GitHub API.
          config: A dict containing the configuration for the GitHub organization.
          pattern: The pattern to search for.
    """
    repos = {}
    for repo in config['project_repos']:
        print('Fetching data for repository: ', end='')
        print('{}/{}...'.format(config['organization'], repo), end='')
        sys.stdout.flush()
        repos[repo] = client.Repository(config['organization'], repo, fetch_issues=False)
        print(DELETE_LINE, end='')

    found_repos = matchRepositories(repos, pattern)

    print('Labels found in the following repositories:')
    for repo in found_repos:
        for label in found_repos[repo]:
            print('  {}/{}: {}'.format(config['organization'], repo, label))


def matchRepositories(repos: dict, pattern: str) -> dict[str, list[str]]:
    """ Matches repositories against a pattern.

        Args:
          repos: A dict of repositories to match.
          pattern: The pattern to match against.

        Returns:
          A dict of repositories that match the pattern.
    """
    matched_repos = {}
    for repo in repos:
        for id in repos[repo].labels:
            label = repos[repo].labels[id].name
            if re.search(pattern, label, re.IGNORECASE):
                if repo not in matched_repos:
                    matched_repos[repo] = []
                matched_repos[repo].append(label)

    return matched_repos


def findAction(actions: list[Action], action: str, label: str) -> int:
    """ Finds an action of the given type and update label.

        Args:
          actions: A list of Actions to search.
          action: The type of action to search for.
          label: The label to search for.

        Returns:
          The index of the action if found, otherwise -1.
    """
    idx = 0 

    for i in actions:
        if i.update.name == label and i.action == action:
            return idx
        idx += 1

    return -1
