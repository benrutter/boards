from typing import Optional, Dict, Annotated, List, Any, Union, Iterable
from pathlib import Path
import shutil
import subprocess
import os

from rich import print, table
import typer
import tomlkit
from send2trash import send2trash


class BoardsApp:
    """
    Central app for boards
    """

    def __init__(
        self,
        board: Annotated[str, typer.Argument()] = "default",
        promote: Annotated[str, typer.Option("--promote", "-p")] = "",
        demote: Annotated[str, typer.Option("--demote", "-d")] = "",
        new: Annotated[str, typer.Option("--new", "-n")] = "",
        notes: Annotated[str, typer.Option("--notes", "--edit", "-e")] = "",
        remove: Annotated[str, typer.Option("--remove", "-r")] = "",
        make_board: Annotated[str, typer.Option("--make-board", "-m")] = "",
        init: Annotated[str, typer.Option("--init", "-i")] = "",
    ):
        """
        Initialise app- all behaviour handled in init loop
        """
        self.user_config: dict = self.get_user_config()
        self.init_board(Path(init)) if init else None
        try:
            self.board_dir: Path = self.get_board_dir(board)
        except KeyError:
            print(f"[red]Board named {board} not found in config[/red]")
            return
        self.board_config: dict = self.get_board_config()
        self.lanes: Any = self.board_config["lanes"]
        self.move(promote, by=1) if promote else None
        self.move(demote, by=-1) if demote else None
        self.new(new) if new else None
        self.edit(notes) if notes else None
        self.remove(remove) if remove else None
        self.make_board(make_board) if make_board else None
        self.display_board()

    def get_board_dir(
        self, board: str, parent_board: Union[Path, str, None] = None
    ) -> Path:
        """
        Figure out the directory for a specific board

        board name found initialy through user config
        subboards can be found through board.subboard
        """
        if board == "default" and Path("board.toml") in Path(".").glob("*.toml"):
            return Path(".")
        boards: List[str] = board.split(".")
        current_board: Union[Path, str]
        if parent_board:
            lanes: List[str] = self.get_board_config(parent_board)["lanes"]
            current_board = self.find_item(
                boards.pop(0),
                Path(parent_board),
                lanes=lanes,
            )
        else:
            current_board = self.user_config["boards"][boards.pop(0)]
        if len(boards) == 0:
            return Path(current_board)
        return self.get_board_dir(
            board=".".join(boards),
            parent_board=current_board,
        )

    def get_user_config(self) -> dict:
        """
        Return user config
        """
        home: str
        if os.name == "nt":
            home = os.environ["USERPROFILE"]
        else:
            home = os.environ["HOME"]
        config_path: Path = Path(home) / ".config" / "boards" / "config.toml"
        if config_path.exists():
            with open(config_path, "r") as file:
                contents: str = file.read()
            return dict(tomlkit.loads(contents))
        print("No existing user config found, creating along with default board")
        default_board: Path = config_path.parent / "userboard"
        self.init_board(default_board)
        config: dict = {
            "boards": {"default": str(default_board)},
            "editor": "vi",
        }
        with open(config_path, "w", encoding="utf-8") as file:
            file.write(tomlkit.dumps(config))
        print(f"[green]Config and board created at {config_path.parent}[/green]")
        return config

    def get_board_config(self, board_dir: Union[str, Path, None] = None) -> dict:
        """
        Return board configuration
        """
        board_dir = board_dir or self.board_dir
        with open(f"{board_dir}/board.toml", "r") as file:
            contents: str = file.read()
        board_config = tomlkit.loads(contents)
        return dict(board_config)

    def get_board_dict(self) -> dict:
        """
        Return board
        """
        lanes: dict = self.board_config["lanes"]
        board_dict: Dict[str, list] = {k: [] for k in lanes}
        counter: int = 1
        for lane in lanes:
            items: Iterable = Path(f"{self.board_dir}/{lane}").glob("*")
            for item in items:
                board_dict[lane] += [f"[{counter}] {item.stem}"]
                counter += 1
        return board_dict

    def display_board(self) -> None:
        """
        Print board out as table
        """
        board_dict: dict = self.get_board_dict()
        board_table: table.Table = table.Table()
        lanes = self.board_config["lanes"]
        icons = self.board_config.get("icons")
        for lane in lanes:
            icon = icons.get(lane) or "" if icons else ""
            board_table.add_column(f"[bold u]{lane}[/bold u] {icon}")
        board_length: int = max([len(i) for i in board_dict.values()])
        display_board: Dict[str, str] = {
            k: v + ["" for i in range(board_length - len(v))]
            for k, v in board_dict.items()
        }
        for i in range(board_length):
            board_table.add_row(*[display_board[k][i] for k in display_board])
        print(board_table)

    def find_item_by_id(self, id: int) -> str:
        for item_list in self.get_board_dict().values():
            for item in item_list:
                if item.startswith(f"[{id}] "):
                    return item.replace(f"[{id}] ", "", 1)
        return id

    def move(self, item: str, by: int) -> None:
        """
        promote selected item to new location
        """
        if item.isnumeric():
            item = self.find_item_by_id(item)
        lane_dirs: List[Path] = [Path(i) for i in self.board_config["lanes"]]
        try:
            found: Path = self.find_item(item)
        except FileNotFoundError:
            print(f"[red]could not find '{item}' on board[/red]")
            return
        move_to_idx: int = self.lanes.index(found.parent.stem) + by
        if move_to_idx >= len(self.lanes) or move_to_idx < 0:
            print(f"[red]Cannot move '{item}' past '{found.parent.stem}'[red]")
            return
        move_to: Path = (
            self.board_dir / lane_dirs[move_to_idx] / (found.stem + found.suffix)
        )
        move_to.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(found, move_to)
        print(f"[green]{item} moved to {move_to.parent.stem}[/green]")

    def new(self, item: str) -> None:
        """
        make new item on board at first lane
        """
        if item.isnumeric():
            print("[red]Item cannot have numeric only name[/red]")
            return
        filepath: Path = self.board_dir / Path(self.lanes[0]) / (item + ".md")
        with open(filepath, "w", encoding="utf-8") as file:
            file.write(f"# {item}\n(edit here to add notes)")

    def edit(self, item: str) -> None:
        """
        Edit item on board with configured text editor
        """
        if item.isnumeric():
            item = self.find_item_by_id(item)
        try:
            found: Path = self.find_item(item)
        except FileNotFoundError:
            print(f"[red]Could not find '{item}' on board[/red]")
            return
        subprocess.run([self.user_config["editor"], found])

    def find_item(
        self,
        item: str,
        board_dir: Union[str, Path, None] = None,
        lanes: Optional[List[str]] = None,
    ) -> Path:
        """
        Get item location
        """
        board_dir = board_dir or self.board_dir
        lanes = lanes or self.lanes
        lane_dirs: List[Path] = [board_dir / Path(i) for i in lanes]
        for lane in lane_dirs:
            items: List[Path] = list(lane.iterdir())
            matches = [i for i in items if i.stem == item]
            if len(matches) > 0:
                return matches[0]
        raise FileNotFoundError()

    def remove(self, item: str) -> None:
        """
        Remove item from board, moving into archive
        """
        if item.isnumeric():
            item = self.find_item_by_id(item)
        try:
            found: Path = self.find_item(item)
        except FileNotFoundError:
            print(f"[red]Could not find '{item}' on board[/red]")
            return
        move_to: Path = (
            self.board_dir
            / Path(self.board_config["bin"])
            / (found.stem + found.suffix)
        )
        move_to.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(found, move_to)
        print(f"[green]'{item}' removed from board")

    def init_board(self, location: Path) -> None:
        """
        create board.toml, plus lanes
        """
        location.mkdir(parents=True, exist_ok=True)
        with open(location / "board.toml", "w", encoding="utf-8") as file:
            file.write('lanes = ["todo", "doing", "done"]\nbin = "archive"')
        for lane in ["todo", "doing", "done"]:
            (location / lane).mkdir()
        print(f"[blue]Board initialised as {location}[/blue]")

    def make_board(self, item) -> None:
        """
        Get file, and replace with directory
        """
        if item.isnumeric():
            item = self.find_item_by_id(item)
        try:
            found: Path = self.find_item(item)
        except FileNotFoundError:
            print(f"[red]Could not find '{item}' on board[/red]")
            return
        send2trash(found)
        self.init_board(found.parent / found.stem)


def run_app():
    app = typer.Typer(
        add_completion=False,
        context_settings={"help_option_names": ["-h", "--help"]},
    )
    app.command()(BoardsApp)
    app()


if __name__ == "__main__":
    run_app()
