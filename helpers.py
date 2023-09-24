'''
This file contains contains helper functions callable by any of the 2 bots.
'''

import logging
import pickle
import pandas as pd


def log(msg, level="INFO") -> None:
    msg = (75*"~")+"\n"+msg+"\n"+(75*"~")+"\n"
    if level == 'INFO':
        logging.info(msg)
    if level == "DEBUG":
        logging.debug(msg)

def df_to_csv(df, csv_path, **kwargs) -> None:
    """Saves DataFrame to csv & preserves dtypes in 2nd line."""
    df2 = df.copy()

    # Replace index with numerical one
    df2.reset_index(drop=True, inplace=True)

    # Prepend dtypes to top of df
    df2.loc[-1] = df2.dtypes
    df2.index = df2.index + 1
    df2.sort_index(inplace=True)

    # Save to csv
    df2.to_csv(csv_path, index=False, **kwargs)


def csv_to_df(csv_path, **kwargs) -> pd.DataFrame:
    """Reads DataFrame from csv with dtypes preserved in 2nd line."""

    try:
        # Read dtypes from 2nd line of csv
        dtypes = {key:value for (key,value) in pd.read_csv(csv_path,
                nrows=1).iloc[0].to_dict().items() if 'date' not in value}
    except KeyError:
        log(f"COULD NOT INFER DTYPES FROM CSV. CHECK {(csv_path).upper()}.")

    parse_dates = [key for (key,value) in pd.read_csv(csv_path,
                   nrows=1).iloc[0].to_dict().items() if 'date' in value]

    # Read the rest of the lines with the dtypes from above
    return pd.read_csv(csv_path, dtype=dtypes, parse_dates=parse_dates, skiprows=[1], **kwargs)


def return_pretty(d, len_lines=None, prefix="\n", suffix="\n") -> str:
    """Some custom string formatting for dictionaries. Skips empty entries."""
    lines = []
    for k,v in d.items():
        if v not in (['', ' ', [], {}]):
            lines.append(str("{:17} | {:<20}".format(k,str(v))))

    # Add borders
    if not len_lines:
        len_lines = max((len(line)) for line in lines)
    line = '='*len_lines
    lines.insert(0, line), lines.append(line)

    return str(prefix+'\n'.join(lines)+suffix)


def iter_to_str(iterable, ignore_list=[], prefix="\n\n", suffix="\n\n") -> str:
    """Parses iterable to string, one entry per line."""
    if iterable == None:
        return ""

    iterable = [str(x) for x in iterable if x not in ignore_list]
    contents = "\n".join(iterable)

    return str(prefix+contents+suffix)


def write_to_pickle(obj, filepath):
    with open(filepath, 'wb') as handle:
        pickle.dump(obj, handle, protocol=pickle.HIGHEST_PROTOCOL)
