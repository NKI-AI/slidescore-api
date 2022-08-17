from slidescore_api.cli import parse_api_token, download_labels, build_client, LabelOutputType
from pathlib import Path


api_token = parse_api_token("/data/slidescore_api_keys/1286_1285.key")
download_labels(slidescore_url="https://slidescore.nki.nl/",
                    api_token=api_token,
                    save_dir=Path("/homes/tkootstra/jsons_test"),
                    study_id="1285",
                    question_type="JSON",
                    output_type="GEOJSON"
                )