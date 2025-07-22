# airpatrol

Python package for interacting with AirPatrol devices.

## Installation

```bash
pip install airpatrol
```

## Usage

```python
from airpatrol.api import AirPatrolAPI
import asyncio
from aiohttp import ClientSession

async def main():
    async with ClientSession() as session:
        api = await AirPatrolAPI.authenticate(session, 'your@email.com', 'password')
        devices = await api.get_devices()
        print(devices)

asyncio.run(main())
```

## Development

- Clone the repo
- Install dependencies: `pip install -r requirements.txt`
- Run tests: `pytest`

## License

MIT License
