import os
from typing import Mapping

import requests

api_base_url = "https://api.github.com"
token = os.environ["GH_TOKEN"]


def parse_link_rels(headers: Mapping[str, str]) -> dict[str, str]:
    link_rels = dict()
    link_headers = headers.get("Link", None)
    if link_headers is None:
        return link_rels
    for link in link_headers.split(","):
        link_rel_pair = link.split(";")
        assert len(link_rel_pair) == 2
        link_rel_pair = [s.strip() for s in link_rel_pair]
        link_rel_pair[0] = link_rel_pair[0][1:-1]  # Remove surrounding angle brackets
        link_rel_pair[1] = link_rel_pair[1][
            5:-1
        ]  # Remove leading 'rel="' and trailing '"'
        assert link_rel_pair[1] in ("prev", "next", "last", "first")
        assert link_rel_pair[1] not in link_rels
        link_rels[link_rel_pair[1]] = link_rel_pair[0]
    return link_rels


# Get followers

followers = set()

headers = {
    "Accept": "application/vnd.github+json",
    "Authorization": f"Bearer {token}",
    "X-GitHub-Api-Version": "2022-11-28",
}
params = {
    "per_page": 100,
    "page": 1,
}
response = requests.get(
    api_base_url + "/user/followers", headers=headers, params=params
)
response.raise_for_status()
json_response = response.json()
for user in json_response:
    username = user["login"]
    assert username not in followers
    followers.add(username)

while True:
    link_rels = parse_link_rels(response.headers)
    next_url = link_rels.get("next", None)
    if next_url is not None:
        response = requests.get(next_url, headers=headers)
        response.raise_for_status()
        json_response = response.json()
        # TODO: reduce code duplication
        for user in json_response:
            username = user["login"]
            assert username not in followers
            followers.add(username)
    else:
        break

print(f"Followers: {len(followers)}")

# Get following

following = set()

response = requests.get(
    api_base_url + "/user/following", headers=headers, params=params
)
response.raise_for_status()
json_response = response.json()
for user in json_response:
    username = user["login"]
    assert username not in following
    following.add(username)

while True:
    link_rels = parse_link_rels(response.headers)
    next_url = link_rels.get("next", None)
    if next_url is not None:
        response = requests.get(next_url, headers=headers)
        response.raise_for_status()
        json_response = response.json()
        # TODO: reduce code duplication
        for user in json_response:
            username = user["login"]
            assert username not in following
            following.add(username)
    else:
        break

print(f"Following: {len(following)}")

# Unfollow non followers
for username in following:
    if username in followers:
        continue
    print(f"Unfollowing {username}")
    response = requests.delete(
        api_base_url + f"/user/following/{username}", headers=headers
    )
    response.raise_for_status()

# Follow followers
headers["Content-Length"] = "0"
for username in followers:
    if username in following:
        continue
    print(f"Following {username}")
    response = requests.put(
        api_base_url + f"/user/following/{username}", headers=headers
    )
    response.raise_for_status()

    # Check if follow was successful
    response = requests.get(
        api_base_url + f"/user/following/{username}", headers=headers
    )
    if response.status_code == 404:
        print(
            f"Failed to follow {username}, maybe https://github.com/{username} is a private GitHub profile?"
        )
    else:
        response.raise_for_status()
