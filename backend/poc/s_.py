import requests


def main():
    uel = "https://api.semanticscholar.org/graph/v1/paper/search"
    params = {
        "query":"AI Agents",
        "limit": 3,
        "fields": "title,abstract,publicationDate,isOpenAccess,tldr"
    }
    res = requests.get(
        "https://api.semanticscholar.org/graph/v1/paper/search/", params=params
    )
    print(res)
    res = res.json()
    print(res)

main()