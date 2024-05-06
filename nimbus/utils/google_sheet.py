import re
import click
import socket
import traceback
import maestro.utils.gcloud as gcloud
from typing import Iterator
from googleapiclient import discovery
from googleapiclient.errors import HttpError


class Cell:
    """Represents a editable cell from a Row in a Google Sheet."""

    def __init__(self, parent: 'Row', index: int, value: str):
        self.parent = parent
        self.index = index
        self.value = value
        self.original_value = self.value

    def get_letter_index(self):
        """Gets the A1 notation key of this cell, uniquely identifying it in our sheet."""
        # using index+1 here since in Python indexes start from 0, but in sheets (for this letter notation), they start from 1.
        letter = columnToLetter(self.index + 1)
        return f"{letter}{self.parent.index + 1}"

    def was_changed(self):
        """Checks if this cell was changed"""
        return self.value != self.original_value

    def save_changes(self):
        """Saves changes made in this cell"""
        self.original_value = self.value

    def __eq__(self, other):
        if isinstance(other, Cell):
            return self.index == other.index and self.value == other.value
        elif isinstance(other, str):
            return self.value == other
        return False

    def __str__(self):
        return str(self.value)

    def __repr__(self):
        return f"{self.parent}.Cell#{self.index} ({self.get_letter_index()})"

    def __hash__(self):
        return hash(self.value)


class Row:
    """Represents a editable row in a Google Sheet."""

    def __init__(self, parent: 'Sheet', index: int, cells):
        self.parent = parent
        self.index = index
        self.cells: list[Cell] = [Cell(self, i, value) for i, value in enumerate(cells)]

    def is_header(self):
        """Checks if this row is a header row"""
        return self.parent.header == self

    def as_dict(self):
        """Returns a dict representation of this row.

        Each key:value pair matches a cell. The key is the cell's value in the header row (same column), and the value is the actual cell's value.
        """
        key_indexes = self.parent.get_header_indexes()
        data: dict[str, str] = {}
        for key, i in key_indexes.items():
            data[key] = self[i].value
        return data

    def __getitem__(self, key) -> Cell:
        if isinstance(key, int):
            # return cell by index
            self._extend_cells_to_index(key)
            return self.cells[key]
        elif isinstance(key, str):
            # return cell by key
            key_indexes = self.parent.get_header_indexes()
            if key not in key_indexes:
                raise KeyError(f"invalid cell key '{key}'")
            index = key_indexes[key]
            self._extend_cells_to_index(index)
            return self[index]
        # TODO: implement slice support and failsafes
        raise KeyError(f"invalid cell index/key '{key}' (a {type(key)} value)")

    def __setitem__(self, key, value):
        self[key].value = value

    def _extend_cells_to_index(self, index):
        """Extends this row's cells up to the given index (inclusive)"""
        if index >= len(self.cells):
            for i in range(len(self.cells), index + 1):
                self.cells.append(Cell(self, i, None))

    def __iter__(self) -> Iterator[Cell]:
        return iter(self.cells)

    def __eq__(self, other):
        if isinstance(other, Row):
            return self.parent == other.parent and self.index == other.index and self.cells == other.cells
        return False

    def __str__(self):
        return f"{self.parent}.Row#{self.index+1}"


class Sheet:
    """Creates a Sheet object with methods to facilitate working with Google Spreadsheets."""

    _service_obj: discovery.Resource = None
    """The Google Sheets API service object. This object is initialized once by a Sheet, and reused for all other Sheets
    to improve loading times."""

    def __init__(self, sheet_id: str, sheet_name: str, verbose=False):
        """* SHEET_ID: sheet hash code. Usually found in URL.
        * SHEET_NAME: the individual table name from the sheet to load.
        * VERBOSE: enable verbose logging.
        """
        self.sheet_id = sheet_id
        self.sheet_name = sheet_name
        self.rows: list[Row] = []
        """The list of rows of this sheet. Each row itself is a list of Cells, ordered from first column to last."""
        self.header: Row = Row(self, -1, [])
        self._header_indexes: dict[str, int] = None
        """This is the header row."""
        self.verbose = verbose

    def set_header_row(self, header_index):
        """Define a row to be used for keying other rows"""
        self.header = self.rows[header_index]
        self._header_indexes = None

    def get_header_indexes(self):
        """Gets a table of {column key -> column index}, based on the cells of the header row.
        This is used to index by a str key the cells of all rows besides the header."""
        if self._header_indexes is None:
            self._header_indexes = {cell.value: index for index, cell in enumerate(self.header)}
        return self._header_indexes

    def get_rows(self):
        """Return all rows that exist after the header index."""
        return self.rows[self.header.index + 1:]

    def get_row(self, index) -> Row:
        """Gets the Row with the given relative INDEX to the header-row."""
        return self.rows[self.header.index + index + 1]

    def add_new_row(self):
        """Adds a new empty row to the end of the sheet."""
        row = Row(self, len(self.rows), [])
        self.rows.append(row)
        return row

    def get_cell(self, key):
        """Gets the cell by its KEY - its A1 notation index."""
        # TODO: allow key ranges as in sheets to return a list of cells?
        values = re.match(r"^([a-zA-Z]+)(\d+)$", key)
        if not values:
            raise KeyError(f"Given key '{key}' is not in A1 notation")
        column_letter = values.group(1)
        # remember A1 key indexes start from 1, and we use from 0 here.
        row_index = int(values.group(2)) - 1
        if row_index >= len(self.rows):
            raise IndexError(f"Row index from A1 key '{key}' is invalid")
        row = self.rows[row_index]
        cell_index = letterToColumn(column_letter) - 1
        return row[cell_index]

    def __getitem__(self, key):
        return self.get_cell(key)

    def __setitem__(self, key, value):
        cell = self[key]
        cell.value = value

    def __iter__(self) -> Iterator[Row]:
        return iter(self.get_rows())

    def get_size(self):
        """Gets the number of rows that exist after the header row."""
        return len(self.get_rows())

    def load(self):
        """Loads the sheet data from this object, using the Robot Tapps service-account for authentication.
        Returns a boolean indicating if loading was successfull or not."""
        retry = 0
        max_retries = 3

        self._log(f"Downloading sheet '{self.sheet_name}'")

        while retry <= max_retries:
            try:
                ranges = [f"'{self.sheet_name}'!A1:ZZ"]

                service = self._get_service()
                result = service.spreadsheets().values().batchGet(spreadsheetId=self.sheet_id, ranges=ranges).execute()
                for index, row_data in enumerate(result["valueRanges"][0].get('values', [])):
                    self.rows.append(Row(self, index, row_data))
                self.set_header_row(0)
                return True
            except socket.timeout:
                if retry <= max_retries:
                    retry += 1
                    self._log(f"Retry {retry} of {max_retries}.", fg="yellow")

            except HttpError:
                self._log(f"No sheet found for '{self.sheet_name}': {traceback.format_exc()}", fg="red", ignore_verbose=True)
                return False
        self._log("Requests timed out, couldn't fetch spreadsheet.", fg="red", ignore_verbose=True)
        return False

    def save(self):
        """Checks all of our cells which had their values changed and saves these changes into the remote sheet."""
        try:
            body = {
                "valueInputOption": "RAW",
                "data": []
            }
            for row in self.rows:
                for cell in row:
                    if cell.was_changed():
                        # NOTE: we're saving by specifying each modified cell as its own range to save in the command.
                        # Since the API allows to save ranges of cells in a single go, this might not be the most efficient method...
                        body["data"].append({
                            "range": f"'{self.sheet_name}'!{cell.get_letter_index()}",
                            "values": [[cell.value]]  # yes, double-list here
                            # values is a list of list of values (so rows of cells) of the values changed in this range.
                            # since we are altering cell-by-cell, its a simple double list with the value.
                        })
                        cell.save_changes()

            num_changes = len(body["data"])
            if num_changes > 0:
                service = self._get_service()
                service.spreadsheets().values().batchUpdate(spreadsheetId=self.sheet_id, body=body).execute()
                self._log(f"Sheet '{self.sheet_name}': saved changes in {num_changes} cells", fg="green")
            else:
                self._log(f"Sheet '{self.sheet_name}': no changes to save", fg="green")
            return True
        except HttpError:
            self._log(f"Couldn't write to sheet '{self.sheet_name}': {traceback.format_exc()}", fg="red", ignore_verbose=True)
            return False

    @classmethod
    def _get_service(cls) -> discovery.Resource:
        """Gets the Google's Resource service, used to call Sheets API commands.
        This uses the Robot Tapps service-account credentials to authenticate the commands.
        """
        if cls._service_obj is None:
            discovery_url = "https://sheets.googleapis.com/$discovery/rest?version=v4"
            # For now use the same scopes for all sheets since its easier and there's been no need for custom scopes per-sheet.
            scopes = [
                'https://www.googleapis.com/auth/spreadsheets.readonly',
                'https://www.googleapis.com/auth/spreadsheets'
            ]
            creds = gcloud.get_robot_tapps_credentials(scopes)
            # TODO: allow authentication with user's personal google account
            cls._service_obj = discovery.build('sheets', 'v4', credentials=creds, discoveryServiceUrl=discovery_url, cache_discovery=False)
        return cls._service_obj

    @classmethod
    def preload_service(cls):
        """Preloads the authentication and Google's Resource service.

        The service is the API used internally to interact with Google Sheets.
        Preloading this may make later calls to `load()` or `save()` in all sheets faster, since initializing the service takes a while."""
        cls._get_service()

    def _log(self, msg, fg="white", ignore_verbose=False):
        """Logs a message to the console if verbose output is enabled."""
        if self.verbose or ignore_verbose:
            click.secho(msg, fg=fg)

    def __str__(self):
        return f"Sheet[{self.sheet_name}]"


def columnToLetter(column):
    """Converts a numerical column index to its equivalent sheets column letter. So:
    * 1 => A
    * 2 => B
    * 26 => Z
    * 27 => AA
    * 29 => AC
    and so on.
    """
    temp = ''
    letter = ''
    while (column > 0):
        temp = (column - 1) % 26
        letter = chr(temp + 65) + letter
        column = int((column - temp - 1) / 26)
    return letter


def letterToColumn(letter):
    """Converts a sheets column letter to its equivalent numerical index. So:
    * A => 1
    * B => 2
    * Z => 26
    * AA => 27
    * AC => 29
    and so on.
    """
    column = 0
    length = len(letter)
    for i in range(length):
        column += (ord(letter[i]) - 64) * 26**(length - i - 1)
    return column
