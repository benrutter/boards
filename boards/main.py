import pathlib

from rich import print, table
import typer
import tomlkit


class BoardsApp:
    def __init__(self, board="default", promote=None, demote=None):
        self.user_config = self.get_user_config()
        self.board_dir = self.user_config["boards"][board]
        self.board_config = self.get_board_config()
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


typer.run(BoardsApp)