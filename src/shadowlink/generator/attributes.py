"""Latent population generation and attribute pools."""

from __future__ import annotations

import datetime
from typing import Any

import numpy as np
import pandas as pd

from shadowlink.generator.models import TimestampWindow

DEFAULT_CITIES: list[str] = [
    "Kolkata",
    "Delhi",
    "Mumbai",
    "Chennai",
    "Bengaluru",
    "Hyderabad",
    "Pune",
    "Jaipur",
]

DEFAULT_COURSES: list[str] = [
    "CSE",
    "ECE",
    "ME",
    "EE",
    "CE",
    "IT",
]

DEFAULT_HOSTELS: list[str] = [
    "Ganga",
    "Yamuna",
    "Brahmaputra",
    "Kaveri",
    "Narmada",
]

DEFAULT_CLUBS: list[str] = [
    "Coding",
    "Robotics",
    "Drama",
    "Music",
    "Literary",
    "Sports",
]

DEFAULT_LOCATIONS: list[str] = [
    "North Campus",
    "South Extension",
    "Salt Lake",
    "Whitefield",
    "Bandra",
    "Cyber City",
]


def generate_latent_population(
    n: int,
    rng: np.random.Generator,
    timestamp_window: TimestampWindow | None = None,
    min_age: int = 17,
    max_age: int = 30,
    cities: list[str] | None = None,
    courses: list[str] | None = None,
    hostels: list[str] | None = None,
    clubs: list[str] | None = None,
    locations: list[str] | None = None,
) -> pd.DataFrame:
    """Generate N latent individuals with correlated/structured demographic profiles.

    Attributes generated per person:
    - entity_id: internal ground-truth identifier E-00000..E-NNNNN
    - age: integer in [min_age, max_age]
    - city: categorical string
    - course: categorical string
    - hostel: categorical string
    - club: categorical string
    - location: categorical area name
    - timestamp: string at minute resolution inside timestamp_window
    """
    c_list = cities or DEFAULT_CITIES
    cr_list = courses or DEFAULT_COURSES
    h_list = hostels or DEFAULT_HOSTELS
    cl_list = clubs or DEFAULT_CLUBS
    loc_list = locations or DEFAULT_LOCATIONS

    ts_win = timestamp_window or TimestampWindow()
    start_dt = datetime.datetime.fromisoformat(ts_win.start_date)
    total_minutes = ts_win.days * 24 * 60

    ages = rng.integers(low=min_age, high=max_age + 1, size=n)
    chosen_cities = rng.choice(c_list, size=n)
    chosen_courses = rng.choice(cr_list, size=n)
    chosen_hostels = rng.choice(h_list, size=n)
    chosen_clubs = rng.choice(cl_list, size=n)
    chosen_locations = rng.choice(loc_list, size=n)

    random_minutes = rng.integers(low=0, high=total_minutes, size=n)
    timestamps = [
        (start_dt + datetime.timedelta(minutes=int(m))).strftime("%Y-%m-%d %H:%M:00")
        for m in random_minutes
    ]

    records: list[dict[str, Any]] = []
    for i in range(n):
        records.append(
            {
                "entity_id": f"E-{i:05d}",
                "age": int(ages[i]),
                "city": str(chosen_cities[i]),
                "course": str(chosen_courses[i]),
                "hostel": str(chosen_hostels[i]),
                "club": str(chosen_clubs[i]),
                "location": str(chosen_locations[i]),
                "timestamp": str(timestamps[i]),
            }
        )

    return pd.DataFrame(records)

