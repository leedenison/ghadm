import unittest
from ghadm.client import Client, Repository, Label, Issue
import ghadm.labels as labels

class TestLabels(unittest.TestCase):

    def test_find_action_empty_list(self):
        self.assertEqual(labels.findAction([], 'test_action', 'test_label'), -1)

    def test_find_action_exists(self):
        actions = [
            self.create_test_action(
                '1',
                self.create_test_repository('1'),
                self.create_test_label('extant', '1'),
                self.create_test_label('update', '1'))]

        self.assertEqual(
                labels.findAction(actions, 'test_action_1', 'test_update_label_1'), 0)

    def test_find_action_does_not_exist(self):
        actions = [
            self.create_test_action(
                '1',
                self.create_test_repository('1'),
                self.create_test_label('extant', '1'),
                self.create_test_label('update', '1'))]

        self.assertEqual(
                labels.findAction(actions, 'test_action_2', 'test_update_label_2'), -1)

    def test_find_action_three_elements(self):
        actions = [
            self.create_test_action(
                '1',
                self.create_test_repository('1'),
                self.create_test_label('extant', '1'),
                self.create_test_label('update', '1')),
            self.create_test_action(
                '2',
                self.create_test_repository('2'),
                self.create_test_label('extant', '2'),
                self.create_test_label('update', '2')),
            self.create_test_action(
                '3',
                self.create_test_repository('3'),
                self.create_test_label('extant', '3'),
                self.create_test_label('update', '3'))]

        self.assertEqual(
                labels.findAction(actions, 'test_action_2', 'test_update_label_2'), 1)

    def test_match_repositories_empty_dict(self):
        self.assertEqual(labels.matchRepositories({}, 'test_pattern'), {})

    def test_match_repositories_exact_match_two_repos(self):
        label_1 = self.create_test_label('extant', '1')
        label_2 = self.create_test_label('extant', '2')
        label_3 = self.create_test_label('extant', '3')
        label_4 = self.create_test_label('extant', '4')

        repositories = {
            'test_repo_id_1': self.create_test_repository(
                '1',
                {
                    'test_extant_id_1': label_1,
                    'test_extant_id_2': label_2,
                    'test_extant_id_3': label_3,
                    'test_extant_id_4': label_4
                }),
            'test_repo_id_2': self.create_test_repository(
                '2',
                {
                    'test_extant_id_1': label_1,
                    'test_extant_id_3': label_3,
                    'test_extant_id_4': label_4
                }),
            'test_repo_id_3': self.create_test_repository(
                '3',
                {
                    'test_extant_id_1': label_1,
                    'test_extant_id_2': label_2
                })
        }

        expected = {
            'test_repo_id_1': ['test_extant_label_2'],
            'test_repo_id_3': ['test_extant_label_2']
        }

        self.assertEqual(
                labels.matchRepositories(repositories, 'test_extant_label_2'), expected)

    
    def test_generate_sync_actions_empty_config(self):
        config = {
            'organization': 'test_org_1',
            'repositories': [],
            'labels': []
        }

        repository = self.create_test_repository('1')
        self.assertEqual(labels.GenerateSyncActions(config, repository), [])
    

    def test_generate_sync_actions_create(self):
        config = {
            'organization': 'test_org_1',
            'repositories': ['test_repo_id_1', 'test_repo_id_2'],
            'labels': {
                'test_cfg_label_1': {
                    'color': 'test_cfg_color_1',
                    'description': 'test_cfg_description_1'
                },
                'test_cfg_label_2': {
                    'color': 'test_cfg_color_2',
                    'description': 'test_cfg_description_2',
                    'synonyms': ['test_cfg_synonym_1']
                }
            }
        }

        update_1 = Label(
            None, 'test_cfg_label_1', 'test_cfg_description_1', 'test_cfg_color_1')

        update_2 = Label(
            None, 'test_cfg_label_2', 'test_cfg_description_2', 'test_cfg_color_2')

        repository = self.create_test_repository('1')

        expected = [
            labels.Action('create', 'test_org_1', repository, None, update_1),
            labels.Action('create', 'test_org_1', repository, None, update_2)]

        self.assertEqual(labels.GenerateSyncActions(config, repository), expected)
    

    def test_generate_sync_actions_edit(self):
        config = {
            'organization': 'test_org_1',
            'repositories': ['test_repo_id_1'],
            'labels': {
                'test_extant_label_1': {
                    'color': 'test_cfg_color_1',
                    'description': 'test_cfg_description_1'
                }
            }
        }

        label_1 = Label(
            'test_extant_id_1',
            'test_extant_label_1',
            'test_extant_description_1',
            'test_extant_color_1')

        update_1 = Label(
            'test_extant_id_1',
            'test_extant_label_1',
            'test_cfg_description_1',
            'test_cfg_color_1')

        repository = self.create_test_repository('1', {'test_extant_id_1': label_1})

        expected = [labels.Action('edit', 'test_org_1', repository, label_1, update_1)]

        self.assertEqual(labels.GenerateSyncActions(config, repository), expected)
    

    def test_generate_sync_actions_relabel(self):
        config = {
            'organization': 'test_org_1',
            'repositories': ['test_repo_id_1'],
            'labels': {
                'test_extant_label_1': {
                    'color': 'test_extant_color_1',
                    'description': 'test_extant_description_1',
                    'synonyms': ['test_cfg_synonym_1']
                }
            }
        }

        label_1 = Label(
            'test_cfg_id_1',
            'test_cfg_synonym_1',
            'test_extant_description_1',
            'test_extant_color_1')

        update_1 = Label(
            'test_extant_id_1',
            'test_extant_label_1',
            'test_extant_description_1',
            'test_extant_color_1')

        repository = self.create_test_repository(
                '1',
                {
                    'test_extant_id_1': label_1,
                    'test_cfg_id_1': update_1
                })

        expected = [labels.Action('relabel', 'test_org_1', repository, label_1, update_1)]

        self.assertEqual(labels.GenerateSyncActions(config, repository), expected)
    

    def create_test_label(self, qualifier: str, ordinal: str):
        return Label(
            'test_{}_id_{}'.format(qualifier, ordinal),
            'test_{}_label_{}'.format(qualifier, ordinal),
            'test_{}_description_{}'.format(qualifier, ordinal),
            'test_{}_color_{}'.format(qualifier, ordinal))


    def create_test_repository(
            self,
            ordinal: str,
            labels: dict[str, Label] = {},
            issues: dict[str, Issue] = {},
            errors: list[str] = []):
        return Repository(
            'test_repo_id_{}'.format(ordinal),
            'test_repo_name_{}'.format(ordinal),
            labels,
            issues,
            errors)


    def create_test_action(
            self,
            ordinal: str,
            repository: Repository,
            extant: Label,
            update: Label):
        return labels.Action(
            'test_action_{}'.format(ordinal),
            'test_org_{}'.format(ordinal),
            repository,
            extant,
            update)
