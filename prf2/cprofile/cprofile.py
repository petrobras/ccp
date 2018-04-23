import sys
import cProfile
import subprocess
from pathlib import Path
from prf2 import Q_, State


def generate_label(caller):
    """Generates a label to the cprofile output file."""
    commit_number = subprocess.check_output(['git', 'describe', '--always'])
    commit_number = str(commit_number, 'utf-8').strip('\n')

    increment = 0
    label = Path(caller + '_'
                 + commit_number + '_'
                 + str(increment)
                 + '.prof')

    while label.exists():
        increment += 1
        label = Path(caller + '_'
                     + commit_number + '_'
                     + str(increment) + '.prof')

    return label


def state():
    State.define(rho=0.9280595769591103, p=Q_(1, 'bar'),
                 fluid={'Methane': 0.5, 'Ethane': 0.5})


if __name__ == '__main__':
    func = sys.argv[1]
    file_name = generate_label(func)
    cProfile.run(func + '()', file_name)


