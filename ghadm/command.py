import sys
import traceback
import argparse

from ghadm.client import Client
import ghadm.labels as labels
import ghadm.config as cfg

LABEL_DESC = 'manage labels for a GitHub organization'
LABEL_SYNC_HELP = 'sync labels for a GitHub organization'
LABEL_SYNC_RELABEL_HELP = 'relabel issues when a synonym is merged as part of a sync (slow)'
LABEL_SEARCH_HELP = 'search for labels in a GitHub organization'
LABEL_SEARCH_PATTERN_HELP = 'pattern to search for'
LABEL_DELETE_HELP = 'delete a label from a GitHub organization'
LABEL_DELETE_LABEL_HELP = 'label to delete'

CMD_DESC = 'manage GitHub objects for an organization'
CMD_EPILOG = 'Reads configuration from ~/.ghadm.yaml'

class CommandUnimplemented(Exception):
    pass

def main():
    config = cfg.ReadConfig()
    if not config:
        sys.exit()

    client = Client(endpoint=config['endpoint'], token=config['access_token'])

    parser = commandParser()
    args = parser.parse_args()

    if not hasattr(args, 'command'):
        print('Error: No command specified')
        parser.print_help()
        sys.exit(1)

    if args.command == 'label':
        if not hasattr(args, 'subcommand'):
            print('Error: No subcommand specified')
            args.subparser.print_help()
            sys.exit(1)

        if args.subcommand and args.subcommand == 'sync':
            labels.Sync(client, config, relabel=args.relabel)
        elif args.subcommand == 'delete':
            labels.DeleteLabel(client, config, args.label)
        elif args.subcommand == 'search':
            labels.SearchLabel(client, config, args.pattern)
        else:
            # argparse should prevent this from happening
            print('Unknown subcommand: {}'.format(args.subcommand))
            sys.exit(1)
    else:
        # argparse should prevent this from happening
        print('Unknown command: {}'.format(args.command))
        sys.exit(1)


def commandParser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
            prog=sys.argv[0].split('/')[-1],
            description=CMD_DESC,
            epilog=CMD_EPILOG)
    subparsers = parser.add_subparsers()

    label_parser = subparsers.add_parser('label', help=LABEL_DESC)
    label_parser.set_defaults(command='label')
    label_parser.set_defaults(subparser=label_parser)
    label_subparsers = label_parser.add_subparsers()

    sync_parser = label_subparsers.add_parser('sync', help=LABEL_SYNC_HELP)
    sync_parser.set_defaults(subcommand='sync')
    sync_parser.add_argument(
            '-r',
            '--relabel',
            action='store_true',
            help=LABEL_SYNC_RELABEL_HELP)

    search_parser = label_subparsers.add_parser('search', help=LABEL_SEARCH_HELP)
    search_parser.set_defaults(subcommand='search')
    search_parser.add_argument(
            '-p',
            '--pattern',
            metavar='PATTERN',
            help=LABEL_SEARCH_PATTERN_HELP,
            required=True)

    delete_parser = label_subparsers.add_parser('delete', help=LABEL_DELETE_HELP)
    delete_parser.set_defaults(subcommand='delete')
    delete_parser.add_argument('label', help=LABEL_DELETE_LABEL_HELP)
    return parser
