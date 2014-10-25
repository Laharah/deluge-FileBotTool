__author__ = 'jaredanderson'
import re

move_to = [
    '[rename] [silicon valley.01x02.avi] to [Silicon Valley s01e02.avi]',
    '[rename] [silicon valley.01x03.avi] to [Silicon Valley s01e03.avi]',
    'processed 2'
]

move_sym = [
    '[rename] [silicon valley.01x02.avi] => [Silicon Valley s01e02.avi]',
    '[rename] [silicon valley.01x03.avi] => [Silicon Valley s01e03.avi]',
    'processed 2'
]

def do_re(data):
    file_moves = []
    for line in data:
        match = re.search(r' \[(.*?)\] (?:(?:to)|(?:=>)) \[(.*?)\]', line)
        if match:
            file_moves.append((match.group(1), match.group(2)))
    return file_moves


print do_re(move_to)
print do_re(move_sym)