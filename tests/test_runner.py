#!/usr/bin/env python2

from argparse import ArgumentParser

import pytest


def _add_parser_args(parser):
    """Adds arguments specific to the unittests"""

    parser.add_argument(
        '--test_dir',
        dest='test_dir',
        default='',
        action='store',
        help='specify test directory'
    )


def main():
    parser = ArgumentParser()
    _add_parser_args(parser)
    arg_space = parser.parse_known_args()[0]

    test_args = ['-x', arg_space.test_dir]

    pytest.main(test_args)


if __name__ == "__main__":
    main()
