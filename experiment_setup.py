HELP_MESSAGE = """
This is a simple script for creating and deleting experiments
in the Microsoft SQL database.

This utility offers five commands:

- new-experiment -f [filename]:
    This adds a new experiment to the database using the
    parameters given in the config file supplied

- delete-experiment -f [filename]:
    This removes an experiment from the database using the
    experiment name given in the config file

- list-backups:
    This prints a list of every available backup file with the date
    and time that they were created. There are a number of flags
    that can be used to filter these results:

    --start : an ISO 8601* datetime format for the earliest date and
        time to search from
    --end : same as 'start' except as the latest date and time to
        search from
    --regex : this is a Pearl-style regular expression for matching
        the filename (not including path or extension)

    Sample querys:
        > python3 experiment_setup.py list-backups --start 2023-02-11 --end 2023-04-01
        This will list all backups from between the 11th of February and the 1st of
        April 2023

        > python3 experiment_setup.py list-backups --start 2023-06-14T14:32:00
        This will list all backups from after the 14th of June 2023 at 2:32:00PM

        > python3 experiment_setup.py list-backups --regex .*50_Percent.*
        This will list all backups containing the substring '50_Percent'

    *ISO 8601 means one of the following two date formats:
    1. '2023-04-15' for the 15th of April 2023
    2. '2023-04-15T16:43:02' for 4:43:02PM on the 15th of April 2023

- restore-from-backup [filename]:
    This restores the database from the given backup file

- help:
    This prints the help message you are currently looking at :)
"""

import builtins
from datetime import datetime
import pathlib
import pyodbc
import re
import sys
import tomllib


# Some (constant) globals
BACKUP_DIRECTORY = pathlib.Path("C:\\something")
DB_ADDR = "test"
DB_NAME = "test"
DB_UID = "user"
DB_PWD = "password"


def handle_database(func):
    """
    Decorator function for any function which connects to the database

    This decorator handles database connections, commits, and
    disconnection. It should be applied to every function which wants
    to make changes to the database.

    Notes:
    Any function which uses this wrapper must take a named cursor
    parameter
    """
    def wrapper(*args):
        conn = pyodbc.connect(
            "DRIVER={ODBC Driver 18 for SQL Server};"
            f"SERVER={DB_ADDR}"
            f"DATABASE={DB_NAME}"
            f"UID={DB_UID}"
            f"PWD={DB_PWD}"
        )
        cursor = conn.cursor()

        result = func(*args, cursor=cursor)

        conn.commit()
        conn.close()

        return result

    return wrapper


""" Utils """

def fix_sql_value_types(value):
    """
    Converts Python values to their appropriate SQL types.

    This means converting boolean values into integer values,
    and then all values are converted to strings.
    
    THIS FUNCTION MUST BE USED FOR ANY VALUE INSERTED INTO THE
    DATABASE.

    args:
    - value: the value whose type will be converted.
    """
    match type(value):
        case builtins.bool:
            return str(int(value))
        case builtins.str:
            return "'" + value + "'"
        case _:
            return str(value)


def get_experiment_id(cursor: pyodbc.Cursor, user_defined_id: str) -> int:
    """
    Gets the numeric experiment ID from the database

    args:
    - cursor: the database cursor
    - user_defined_id: the string id of the experiment

    returns:
    the numeric experiment ID, or throws an error
    """
    query = "SELECT * FROM Experiments WHERE UserDefinedID = " + user_defined_id

    return cursor.execute(query).fetchone()


def parse_arguments(argument_list: [str]) -> ([str], {str : str}):
    """
    Turns the argument list into a list of sequential arguments
    and a dictionary of flags with their keys.

    args:
    - argument_list: the list of arguments to parse
    """
    sequential = []
    flags_dict = {}
    index = 0

    while index < len(argument_list):
        if (arg := argument_list[index])[0] == "-":
            if index + 1 < len(argument_list):
                flags_dict[arg] = argument_list[index + 1]
            else:
                raise EOFError(f"flag '{arg}' has no corresponding value")

            index += 2
        else:
            sequential.append(arg)
            index += 1

    return sequential, flags_dict


""" Commands """

@handle_database
def create_new_experiment(arguments: [str], cursor: pyodbc.Cursor = None):
    """
    Adds a new experiment to the database
    
    args:
    - arguments: the sequential arguments from the command line
        (not including the method name 'new-experiment')
    - cursor: a named parameter which is passed to the function
        by the @handle_database decorator, which represents a
        handle to the database

    This method will raise an exception if the config file doesn't
    contain the required parameters
    """

    if len(arguments) != 1:
        raise SyntaxError(f"too many arguments given to new-experiment\n\n{HELP_MESSAGE}")

    with open(arguments, "rb") as f:
        config = tomllib.load(f)

    # Add experiment info
    info_field_names  = config["info"].keys()
    info_field_values = [fix_sql_value_types(v) for v in config["info"].values()]
    cursor.execute(
        f"INSERT INTO Experiments ({info_field_names}) "
        f"VALUES ({info_field_values})"
    )

    # get experiment ID
    user_defined_id = config["info"]["UserdefinedID"]
    experiment_id = get_experiment_id(cursor, user_defined_id)

    # Add experiment parameters
    parameters = list(config["parameters"].items())
    cursor.execute(
        "INSERT INTO ExperimentParameters "
        "(ExperimentID, ParameterName, ParamValueTxt) VALUES"
        f"({experiment_id}, ?, ?)",
        parameters
    )


@handle_database
def delete_experiment(arguments: [str], cursor: pyodbc.Cursor = None):
    """
    Removes an experiment from the database 

    args:
    - arguments: the sequential arguments from the command line
        (not including the method name 'delete-experiment')
    - cursor: a named parameter which is passed to the function
        by the @handle_database decorator, which represents a
        handle to the database

    This method raises an exception if the UserDefinedID is not found
    in the database
    """
    raise NotImplementedError("I need to read David's 'DeleteExperiment' macro")

    if len(arguments) != 1:
        raise SyntaxError(f"too many arguments given to new-experiment\n\n{HELP_MESSAGE}")

    with open(arguments, "rb") as f:
        config = tomllib.load(f)

    user_defined_id = config["info"]["UserDefinedID"]
    experiment_id = get_experiment_id(cursor, user_defined_id)

    cursor.execute("DELETE FROM Experiments WHERE UserDefinedID = ?", user_defined_id)
    cursor.execute("DELETE FROM ExperimentParameters WHERE ExperimentID = ?", experiment_id)


def list_database_backups(flags: {str : str}):
    """
    Prints a list of all backups, filtered according to
    the command line flags supplied.

    args:
    - flags: the key/value flags from the command line arguments

    note:
    This method will stop working in the year 9999CE
    """
    raise NotImplementedError("I don't yet know where backups are stored")

    global BACKUP_DIRECTORY
    backup_files = []

    # Get search constraints from flags
    start = datetime.fromisoformat(flags.get("--start", "1970-01-01T00:00:00")).timestamp()
    end   = datetime.fromisoformat(flags.get("--end", "9999-01-01T00:00:00")).timestamp()
    regex = re.compile(flags.get("--regex", r".*"))

    for filepath in BACKUP_DIRECTORY.iterdir():
        if start <= (creation_date := filepath.stat().st_ctime) <= end:
            if filepath.suffix == ".bak" and regex.match(filepath.stem):
                backup_files.append((filepath, creation_date))

    for filepath, creation_date in sorted(backup_files, key=lambda p : p[1]):
        creation_date = datetime.fromtimestamp(creation_date).isoformat()
        print(f"{creation_date} - '{filepath}'")


@handle_database
def restore_from_backup(arguments: [str], cursor: pyodbc.Cursor = None):
    """
    Restores an experiment from a specific backup file

    args:
    - arguments: the sequential args from the command line
    """
    global BACKUP_DIRECTORY

    if len(arguments) == 2:
        backup_filepath = pathlib.Path(arguments[1])
    else:
        raise SyntaxError(
            "Bad syntax - expected the following\n"
            "> python3 experiment_setup.py restore-from-backup [filename]"
        )

    if not backup_filepath.is_absolute():
        backup_filepath = BACKUP_DIRECTORY / backup_filepath

    check = input(
        "Are you sure that this is the correct filename? '{backup_filepath}'\n"
        "type 'yes' to confirm: "
    )

    if check == "yes":
        raise NotImplementedError("I don't yet know the scheme for restoring experiments")
    else:
        print("The database has not been changed. Goodbye :)")


if __name__ == "__main__":
    args, flags = parse_arguments(sys.argv[1:])

    match args:
        case ["delete-experiment"]:
            delete_experiment(flags)
        case ["help"]:
            print(HELP_MESSAGE)
        case ["list-backups"]:
            list_database_backups(args[1:])
        case ["new-experiment"]:
            create_new_experiment(args[1:])
        case ["restore-from-backup"]:
            restore_from_backup(args)
        case [command]:
            raise EnvironmentError(f"Unknown command {command}\n\n{HELP_MESSAGE}")
        case []:
            raise EnvironmentError(f"No command given\n\n{HELP_MESSAGE}")
        case _:
            raise EnvironmentError(f"Too many arguments\n\n{HELP_MESSAGE}")
