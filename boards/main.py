from typing import Optional
import pathlib
import shutil

from rich import print, table
import typer
import tomlkit


class BoardsApp:
    def __init__(self, board="default", promote="", demote=""):
        self.user_config = self.get_user_config()
        self.board_dir = pathlib.Path(self.user_config["boards"][board])
        self.board_config = self.get_board_config()
        self.lanes = self.board_config["lanes"]
        if promote:
            self.promote(promote)
        self.board = self.get_board()
        self.display_board()

    def get_user_config(self):
        """
        Return user config
        """
        return {"boards": {"default": "board"}}

    def get_board_config(self):
        """
        Return board configuration
        """
        with open(f"{self.board_dir}/board.toml", "r") as file:
            contents = file.read()
        board_config = tomlkit.loads(contents)
        return board_config

    def get_board(self):
        """
        Return board
        """
        lanes = self.board_config["lanes"]
        board_dict = {k: [] for k in lanes}
        for lane in lanes:
            items = pathlib.Path(f"{self.board_dir}/{lane}").glob("*")
            for item in items:
                board_dict[lane] += [item.stem]
        return board_dict

    def display_board(self):
        """
        Print board out as table
        """
        board_table = table.Table()
        lanes = self.board_config["lanes"]
        for lane in lanes:
            board_table.add_column(lane)
        board_length = max([len(i) for i in self.board.values()])
        display_board = {
            k: v + ['' for i in range(board_length - len(v))]
            for k, v in self.board.items()
        }
        for i in range(board_length):
            board_table.add_row(*[display_board[k][i] for k in display_board])
        print(board_table)

    def promote(self, item):
        """
        promote selected item to new location
        steps:
        1. find item
        2. move item
        """
        lane_dirs: List[Path] = [self.board_dir / pathlib.Path(i) for i in self.lanes]
        found: Optional[Path] = None
        for lane in lane_dirs:
            items: List[Path] = list(lane.iterdir())
            matches = [i for i in items if i.stem == item]
            if len(matches) > 0:
                found: Path = matches[0]
                found_in: Path = lane
                break
        if not found:
            print(f"[red]Could not find {item} in board[/red]")
            return
        move_to = self.lanes.index(found_in.stem) + 1
        if move_to >= len(self.lanes):
            print(f"[red]Cannot promote {item} past {found_in.stem}[red]")
            return
        shutil.move(found, lane_dirs[move_to] / (found.stem + found.suffix))

typer.run(BoardsApp)