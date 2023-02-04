# Grouped Task

This is example of grouped tasks



```python
# tasks/grouped.py
import random
from workflow.api import task


@task(name="RANDOM")
def generate_random(*args, **kwargs):
    payload = kwargs["payload"]
    print("payload %s" % payload)
    return random.randint(payload.get("start", 0), payload.get("end", 10))


@task(name="ADD")
def add_randoms(*args, **kwargs):
    return sum(args[0])

```

And its YAML file

```yaml
#grouped.yaml
# Group of tasks example
#
# +----------+       +----------+
# |  RANDOM  |       |  RANDOM  |
# +----+-----+       +-----+----+
#      |     +-------+     |
#      +---->+  ADD  <-----+
#            +-------+
#
grouped.RANDOMS:
  tasks:
    - GROUP_RANDOMS:
        type: group
        tasks:
          - RANDOM
          - RANDOM
    - ADD
```