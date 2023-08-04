# This is a simple script for creating and deleting experiments in the Microsoft SQL database.

## Commands
- new-experiment [filename]:
    This adds a new experiment to the database using the
    parameters given in the config file supplied

- delete-experiment [filename]:
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
        the filename (not including path or extension). The regex
        must be surrounded with a '/' character

    Sample querys:
    - `> python3 experiment_setup.py list-backups --start 2023-02-11 --end 2023-04-01`
    This will list all backups from between the 11th of February and the 1st of April 2023

    - `> python3 experiment_setup.py list-backups --start 2023-06-14T14:32:00`
    This will list all backups from after the 14th of June 2023 at 2:32:00PM

    - `> python3 experiment_setup.py list-backups --regex /.*50_Percent.*/`
    This will list all backups containing the substring '50_Percent'

- restore-from-backup [filename]:
    This restores the database from the given backup file

## Status
Currently none of these have been tested with the actual database
