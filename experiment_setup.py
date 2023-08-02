HELP_MESSAGE = """
This is a simple script for creating and deleting experiments
in the Microsoft SQL database.

This utility offers three commands:

- new-experiment [filename]:
    This adds a new experiment to the database using the
    parameters given in the config file supplied

- delete-experiment [filename]:
    This removes an experiment from the database using the
    experiment name given in the config file
"""

import builtins
import pyodbc
import sys
import tomllib

# Database authentication
DB_ADDR = "test"
DB_NAME = "test"
DB_UID = "user"
DB_PWD = "password"


def handle_database(func):
    """
    Decorator function for any function which connects to the database

    This decorator handles database connections, commits, and disconnection.
    It should be applied to every function which wants to make changes to the
    database.

    Notes:
    Any function which uses this wrapper must take a 
    """
    def wrapper(config_filename: str):
        conn = pyodbc.connect(
            "DRIVER={ODBC Driver 18 for SQL Server};"
            f"SERVER={DB_ADDR}"
            f"DATABASE={DB_NAME}"
            f"UID={DB_UID}"
            f"PWD={DB_PWD}"
        )
        cursor = conn.cursor()

        result = func(cursor, config_filename)

        conn.commit()
        conn.close()

        return result

    return wrapper


""" Utils """

def fix_sql_value_types(value):
    """
    Converts Python values to their appropriate SQL types

    args:
    - value: the value whose type will be converted.

    This means converting bools to ints and then everything to strings
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


""" Database interaction """

@handle_database
def create_new_experiment(cursor: pyodbc.Cursor, config_filename: str):
    """
    Adds a new experiment to the database
    
    args:
    - config_filename: the name of the config file of the experiment
      to be added to the database

    This method will raise an exception if the config file doesn't
    contain the required parameters
    """

    with open(config_filename, "rb") as f:
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
def delete_experiment(cursor: pyodbc.Cursor, config_filename: str):
    """
    Removes an experiment from the database 

    args:
    - config_filename: the name of the config file of the experiment
      to be deleted

    This method raises an exception if the UserDefinedID is not found
    in the database
    """
    raise NotImplementedError("I need to read David's 'DeleteExperiment' macro")

    with open(config_filename, "rb") as f:
        config = tomllib.load(f)

    user_defined_id = config["info"]["UserDefinedID"]
    experiment_id = get_experiment_id(cursor, user_defined_id)

    cursor.execute("DELETE FROM Experiments WHERE UserDefinedID = ?", user_defined_id)
    cursor.execute("DELETE FROM ExperimentParameters WHERE ExperimentID = ?", experiment_id)


if __name__ == "__main__":
    if len(sys.argv) == 3:
        command, config_filename = sys.argv[1:]
    else:
        print(HELP_MESSAGE)

    match command:
        case "new-experiment":
            create_new_experiment(sys.argv[2])
        case "delete-experiment":
            delete_experiment(sys.argv[2])
        case _:
            raise NameError(f"unknown command {command}\n\n{HELP_MESSAGE}")
