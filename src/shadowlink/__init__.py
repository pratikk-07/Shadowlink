"""SHADOWLINK — Privacy Re-identification Risk Assessment Platform.

DEFENSIVE USE ONLY.  No real personal data, no network calls, no ground-truth
identity columns are accepted by any public API in this package.

Quickstart
----------
>>> import pandas as pd
>>> from shadowlink.profiler.profiler import profile_dataframe
>>> df = pd.read_csv("tests/fixtures/tiny_people_a.csv")
>>> profile = profile_dataframe(df, dataset_name="A")
>>> print(profile.to_json())
"""

__version__ = "0.1.0"
__author__ = "SHADOWLINK Team"
