from gql import Client as GQLClient, gql
from gql.transport.aiohttp import AIOHTTPTransport

PAGE_SIZE = 100

class MissingGraphData(Exception):
    pass


class Label:
    def __init__(self, id: str, name: str, description: str, color: str):
        self.id = id
        self.name = name
        self.description = description
        self.color = color

    def __repr__(self):
        return 'Label<{}, {}, {}, {}>'.format(
            repr(self.id),
            repr(self.name),
            repr(self.description),
            repr(self.color))

    def __eq__(self, other): 
        if not isinstance(other, Label):
            return False

        return (self.id == other.id and
                self.name == other.name and
                self.description == other.description and
                self.color == other.color)

    def DictFromNodes(nodes: dict) -> dict[str, 'Label']:
        labels = {} 

        for n in nodes:
            labels[n['id']] = Label(
                n.get('id'),
                n.get('name'),
                n.get('description', ''),
                n.get('color', ''))

        return labels


class Issue:
    def __init__(self, id: str, title: str, labels: str):
        self.id = id
        self.title = title
        self.labels = labels

    def __repr__(self):
        return '<{}, {}, {}>'.format(
            repr(self.id),
            repr(self.title),
            repr(self.labels))

    def __eq__(self, other): 
        if not isinstance(other, Issue):
            return False

        return (self.id == other.id and
                self.title == other.title and
                self.labels == other.labels)

    def DictFromNodes(nodes: dict) -> tuple[dict[str, 'Issue'], list[str]]:
        issues = {} 
        errors = []

        for n in nodes:
            labels = []
            if n.get('labels'):
                if n['labels']['pageInfo']['hasNextPage']:
                    errors.append('FATAL: Issue {} has more than {} labels: {}'.format(
                        n['id'], PAGE_SIZE, n['name']))

                labels = Label.DictFromNodes(n['labels']['nodes'])

            issues[n['id']] = Issue(
                n.get('id'),
                n.get('title'),
                labels)

        return (issues, errors)


class Repository:
    def __init__(
            self,
            id: str,
            name: str,
            labels: dict[str, Label],
            issues: dict[str, Issue],
            errors: list[str]):
        self.id = id
        self.name = name
        self.labels = labels
        self.issues = issues
        self.errors = errors
        self.labels_by_lower_name = None
        self.issues_by_label = {}

    def __str__(self):
        print(self.name)

    def __repr__(self):
        return '<{}, {}, {}, {}, {}>'.format(
            repr(self.id),
            repr(self.name),
            repr(self.labels),
            repr(self.issues),
            repr(self.errors))

    def __eq__(self, other): 
        if not isinstance(other, Repository):
            return False

        return (self.id == other.id and
                self.name == other.name and
                self.labels == other.labels and
                self.issues == other.issues and
                self.errors == other.errors)

    def LabelsByLowerName(self) -> dict[str, Label]:
        if not self.labels_by_lower_name:
            self.labels_by_lower_name = {}

            for id in self.labels:
                if not self.labels[id].name:
                    raise MissingGraphData()

                lc_name = self.labels[id].name.lower()
                self.labels_by_lower_name[lc_name] = self.labels[id]

        return self.labels_by_lower_name

    def IssuesByLabel(self, label: str) -> list[Issue]:
        if label not in self.issues_by_label:
            result = []

            for issue in self.issues:
                if label in self.issues[issue].labels:
                    result.append(self.issues[issue])

            self.issues_by_label[label] = result

        return self.issues_by_label[label]

    @classmethod
    def FromGraphQL(cls, graph: dict) -> 'Repository':
        if 'issues' in graph['repository']:
            (issues, errors) = Issue.DictFromNodes(graph['repository']['issues']['nodes'])
        else:
            issues = {}
            errors = []

        return Repository(
            graph['repository']['id'],
            graph['repository']['name'],
            Label.DictFromNodes(graph['repository']['labels']['nodes']),
            issues,
            errors)


class Client:
    def __init__(self, endpoint: str, token: str):
        self.transport = AIOHTTPTransport(
            url=endpoint,
            headers={
                'Authorization': 'Bearer ' + token,
                'Accept': 'application/vnd.github.bane-preview+json'
            })
        self.client = GQLClient(
            transport=self.transport,
            fetch_schema_from_transport=False)

    def User(self) -> str:
        result = self.client.execute(gql('''
            query { 
              viewer {
                login 
              }
            }
        '''))

        return result['viewer']['login']

    def Repository(self, org: str, repo: str, fetch_issues: bool) -> Repository:
        """ Queries a repository with all issues and labels.

            Returns an error for each issue which has more than PAGE_SIZE labels.
        """
        has_next_page = True
        issues_after = None
        labels_after = None
        graph = None

        q_issues_after = ''
        q_issues = ''
        if fetch_issues:
            q_issues_after = '$issues_after: String,'
            q_issues = '''issues(first: $first, after: $issues_after) {
                  nodes {
                    id,
                    title,
                    labels(first: $first) {
                      nodes {
                        id
                      },
                      pageInfo {
                        hasNextPage
                      }
                    }
                  },
                  pageInfo {
                    hasNextPage,
                    endCursor
                  }
                },
            '''

        q = gql('''
            query Repository (
              $owner: String!,
              $name: String!,
              $first: Int!,
              ''' + q_issues_after + '''
              $labels_after: String) { 
              repository(owner: $owner, name: $name) {
                id,
                name,
                ''' + q_issues + '''
                labels(first: $first, after: $labels_after) {
                  nodes {
                    id,
                    name,
                    color,
                    description
                  },
                  pageInfo {
                    hasNextPage,
                    endCursor
                  }
                }
              }
            }
        ''')


        while has_next_page: 
            vv = {
                'owner': org,
                'name': repo,
                'labels_after': labels_after,
                'first': PAGE_SIZE
            }

            if fetch_issues:
                vv['issues_after'] = issues_after

            result = self.client.execute(q, variable_values=vv)

            if not graph:
                graph = result
            else:
                labels = result['repository']['labels']['nodes']
                graph['repository']['labels']['nodes'] += labels

                if fetch_issues:
                    issues = result['repository']['issues']['nodes']
                    graph['repository']['issues']['nodes'] += issues

            has_next_page = (result['repository']['labels']['pageInfo']['hasNextPage'] or
                fetch_issues and result['repository']['issues']['pageInfo']['hasNextPage'])
            label_after = result['repository']['labels']['pageInfo']['endCursor']

            if fetch_issues:
                issues_after = result['repository']['issues']['pageInfo']['endCursor']

        return Repository.FromGraphQL(graph)

    def CreateLabel(self, repo: Repository, label: Label):
        m = gql('''
            mutation CreateLabel($l: CreateLabelInput!) { 
              createLabel(input: $l) {
                label {
                  name
                }
              }
            }
        ''')

        vv = {
            'l': {
                'name': label.name,
                'color': label.color,
                'description': label.description,
                'repositoryId': repo.id
            }
        }

        self.client.execute(m, variable_values=vv)
        
    def EditLabel(self, extant: Label, update: Label):
        m = gql('''
            mutation UpdateLabel($l: UpdateLabelInput!) { 
              updateLabel(input: $l) {
                label {
                  name
                }
              }
            }
        ''')

        vv = {
            'l': {
                'name': update.name,
                'color': update.color,
                'description': update.description,
                'id': extant.id
            }
        }

        self.client.execute(m, variable_values=vv)

    def Relabel(self, issues: list[Issue], extant: Label, update: Label):
        for issue in issues:
            issue.labels.pop(extant.id, None)
            
            if not issue.labels.get(update.id):
                issue.labels[update.id] = update

            m = gql('''
                mutation UpdateIssue($i: UpdateIssueInput!) { 
                  updateIssue(input: $i) {
                    issue {
                      id
                    }
                  }
                }
            ''')

            vv = {
                'i': {
                    'labelIds': list(issue.labels.keys()),
                    'id': issue.id
                }
            }

            self.client.execute(m, variable_values=vv)

        self.DeleteLabel(extant)

        
    def DeleteLabel(self, extant: Label):
        d = gql('''
            mutation DeleteLabel($l: DeleteLabelInput!) { 
              deleteLabel(input: $l) {
                clientMutationId
              }
            }
        ''')

        vv = {
            'l': {
                'id': extant.id
            }
        }

        self.client.execute(d, variable_values=vv)
