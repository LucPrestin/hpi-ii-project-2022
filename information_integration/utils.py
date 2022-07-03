import json
from typing import List

import requests


def get_used_ids(topic) -> List[str]:
    ids = []

    overview_response = requests.get(url=f'http://localhost:9200/{topic}/_search')
    if overview_response.ok:
        num_hits = overview_response.json()['hits']['total']['value']
        header = {'Content-Type': 'application/json'}
        query = {'query': {'match_all': {}}, 'fields': ['id']}
        url = f'http://localhost:9200/{topic}/_search?scroll=10m&size={num_hits}'

        id_response = requests.get(
            url=url,
            headers=header,
            data=json.dumps(query)
        )

        if id_response.ok:
            result = id_response.json()
            ids = list(map(
                lambda hit: hit['fields']['id'][0],
                result['hits']['hits']
            ))

    return ids
