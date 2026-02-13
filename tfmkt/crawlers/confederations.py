import json

DEFAULT_CONFEDERATION_HREFS = [
    '/wettbewerbe/europa',
    '/wettbewerbe/amerika',
    '/wettbewerbe/afrika',
    '/wettbewerbe/asien',
]


async def run(parents_arg=None, season=2024, base_url=None):
    for href in DEFAULT_CONFEDERATION_HREFS:
        print(json.dumps({'type': 'confederation', 'href': href}), flush=True)
