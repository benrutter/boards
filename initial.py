import glob
import pathlib

from rich import print
from rich import table
import tomlkit

with open("board/board.toml", "r") as file:
    contents = file.read()
config = tomlkit.loads(contents)

todo = table.Table()
for lane in config["lanes"]:
    todo.add_column(lane)

board = {k: [] for k in config["lanes"]}
for lane in config["lanes"]:
    items = pathlib.Path(f"board/{lane}").glob("*")
    for item in items:
        board[lane] += [item.stem]

# now we need to make sure everything's the same length
board_length = max([len(i) for i in board.values()])
board = {
    k: v + ['' for i in range(board_length - len(v))]
    for k, v in board.items()
}

for i in range(board_length):
    todo.add_row(*[board[k][i] for k in board])

print(todo)