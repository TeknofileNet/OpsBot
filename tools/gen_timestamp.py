from __future__ import annotations

import random
from datetime import datetime
from datetime import timedelta

now = datetime.now()
timestamps = []

for _ in range(200):
    # Generate a random number of seconds within the past year
    delta = timedelta(seconds=random.randint(0, 365*24*60*60))
    ts = now - delta
    timestamps.append(ts.strftime('%Y-%m-%d %H:%M:%S'))

# Ensure uniqueness
timestamps = list(set(timestamps))
while len(timestamps) < 200:
    delta = timedelta(seconds=random.randint(0, 365*24*60*60))
    ts = now - delta
    formatted = ts.strftime('%Y-%m-%d %H:%M:%S')
    if formatted not in timestamps:
        timestamps.append(formatted)

# Print the timestamps
for t in timestamps:
    print(t)
