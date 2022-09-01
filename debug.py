from slidescore_api.cli import parse_api_token, build_client, download_labels
from pathlib import  Path
token = parse_api_token("/data/slidescore_api_keys/1285.key")

client = build_client("https://slidescore.nki.nl/", token)

kek = download_labels("https://slidescore.nki.nl/",
                      token,
                      1285,
                      save_dir=Path("/homes/tkootstra/slidescoretest/")
                      )