# coding=utf-8
# Copyright (c) Jonas Teuwen
import argparse
import csv
import json
import logging
import os
import pathlib
import sys
from enum import Enum
from pathlib import Path
from typing import Optional, Iterable

from tqdm import tqdm

from slidescore_api.api import APIClient, SlideScoreResult, build_client
from slidescore_api.logging import build_cli_logger
from slidescore_api.utils.annotations import (SlideScoreAnnotations,
                                              save_shapely)

logger = logging.getLogger(__name__)

# TODO: This are the names of the shapes.
ANNOSHAPE_TYPES = ["polygon", "rect", "ellipse", "brush", "heatmap"]


class LabelOutputType(Enum):
    json: str = "json"
    raw: str = "str"
    shapely: str = "shapely"


def parse_api_token(data: Optional[Path] = None) -> str:
    """
    Parse the API token from file or from the SLIDESCORE_API_KEY. If file is given, this will overwrite the
    environment variable.

    Parameters
    ----------
    data : str or pathlib.Path
    Returns
    -------
    str
        SlideScore API Token.
    """
    if data is not None and pathlib.Path(data).is_file():
        # load token
        with open(data, "r") as file:
            api_token = file.read().strip()
    else:
        api_token = os.environ.get("SLIDESCORE_API_KEY", "")

    if not api_token:
        logging.error(
            "SlideScore API token not properly set. "
            "Either pass API token file, or set the SLIDESCORE_API_KEY environmental variable."
        )
        sys.exit()
    return api_token


def _upload_labels(args: argparse.Namespace) -> None:
    """Main function that uploads labels to SlideScore.

    Parameters
    ----------
    args: argparse.Namespace
        The arguments passed from the CLI. Run with `-h` to see the required parameters

    Returns
    -------
    None
    """
    url = args.slidescore_url
    api_token = parse_api_token(args.token_path)
    study_id = args.study_id
    client = APIClient(url, api_token)
    wsi_results = []

    # Increase csv field size limit for large rows
    try:
        csv.field_size_limit(sys.maxsize)
    except OverflowError:
        csv.field_size_limit(int(sys.maxsize / 10))

    with open(args.results_file, "r") as csvfile:
        reader = csv.DictReader(
            csvfile, delimiter=args.csv_delimiter, fieldnames=args.csv_fieldnames
        )
        for row in reader:
            image_id = row["imageID"]
            image_name = row["imageName"]
            user = row["user"] if args.user is None else args.user
            question = row["question"]
            answer = row["answer"].replace("'", '"') + "\n"

            wsi_result = SlideScoreResult(
                {
                    "imageID": image_id,
                    "imageName": image_name,
                    "user": user,
                    "question": question,
                    "answer": answer,
                }
            )
            wsi_results.append(wsi_result)

    client.upload_results(study_id, wsi_results)


# TODO: This is how to actually retrieve the questions. Think about a proper way to do this.
def retrieve_questions(
    slidescore_url: str,
    api_token: str,
    study_id: int,
    disable_certificate_check: bool = False,
) -> dict:
    """
    Retrieve the questions for a given study from SlideScore.

    This call requires specific permissions, as it obtains the configuration of a given study.

    Parameters
    ----------
    slidescore_url: str
        Url of the slidescore server e.g.: https://rhpc.nki.nl/slidescore/ (without Api/).
    api_token: str
        SlideScore API token.
    study_id: int
        Study id as used by SlideScore.
    disable_certificate_check : bool

    Returns
    -------

    """
    client = build_client(slidescore_url, api_token, disable_certificate_check)

    # Get the configuration for this study. Requires specific permissions.
    config = client.get_config(study_id)
    scores = config["scores"]
    return scores


def write_shapely_to_disc(
    annotation_file_path: Path, study_id: str, author: str, label: str, ann_type: list
) -> None:
    reader = SlideScoreAnnotations(Path(annotation_file_path))
    for idx, curr_annotation in enumerate(
        reader.from_iterable(filter_author=author, filter_label=label)
    ):
        save_shapely(curr_annotation, study_id=study_id, filter_type=ann_type)
    reader.check()


def _save_label_as_json(save_dir, image_id, image, annotations):
    annotation_data = {
        "image_id": image_id,
        "study_id": image["studyID"],  # TODO: image must become a class / NamedTuple
        "image_name": image["name"],
        "annotations": [],
    }

    for annotation in annotations:
        data = annotation.points
        if not data:
            continue

        annotation_data["annotations"].append(
            {"user": annotation.user, "question": annotation.question, "data": data}
        )

    # Now save this to JSON.
    with open(save_dir / f"{image_id}.json", "w") as file:
        json.dump(annotation_data, file, indent=2)


def _row_iterator(slidescore_annotations: Iterable[SlideScoreResult]):
    for annotation in slidescore_annotations:
        yield annotation.to_row()


def download_labels(
    slidescore_url: str,
    api_token: str,
    study_id: int,
    save_dir: Path,
    output_type: LabelOutputType,
    email: Optional[str] = None,
    question: Optional[str] = None,
    disable_certificate_check: bool = False,
) -> None:
    # TODO: Add format to docstring
    """
    Downloads all available annotations for a study on SlideScore from
    one specific author and saves them in a JSON file per image.

    Parameters
    __________
    slidescore_url: str
        Url of the slidescore server e.g.: https://rhpc.nki.nl/slidescore/ (without Api/).
    api_token: str
        SlideScore API token.
    study_id: int
        Study id as used by SlideScore.
    save_dir: Path
        Directory to save the labels to.
    email: str, optional
        The author email/name as registered on SlideScore to download those specific annotations.
    question : str
        The question to obtain the labels for. If not given all labels will be obtained.
    disable_certificate_check : bool
        Disable HTTPS certificate check.

    Returns
    -------
    None
    """
    client = build_client(slidescore_url, api_token, disable_certificate_check)

    if not save_dir.is_dir():
        save_dir.mkdir()

    extra_kwargs = {}
    if email is not None:
        extra_kwargs["email"] = email
    if question is not None:
        extra_kwargs["question"] = question

    # TODO: Images should become a class / NamedTuple
    images = client.get_images(study_id)

    for image in tqdm(images):
        image_id = image["id"]
        annotations = client.get_results(study_id, imageid=image_id, **extra_kwargs)

        if output_type == LabelOutputType.json.value:
            _save_label_as_json(save_dir, image_id, image, annotations)
        elif output_type == LabelOutputType.raw.value:
            with open("annotations.txt", "a") as f:
                for annotation in annotations:
                    f.write(annotation.to_row() + "\n")
        elif output_type == LabelOutputType.shapely.value:
            annotation_parser = SlideScoreAnnotations()
            row_iterator = _row_iterator(annotations)

            for idx, curr_annotation in enumerate(
                annotation_parser.from_iterable(row_iterator)
            ):
                # TODO: Ajey, for you to debug ;-)
                print(curr_annotation)
        else:
            raise RuntimeError(f"Output type not supported.")


def _download_labels(args: argparse.Namespace) -> None:
    """Main function that downloads labels from SlideScore.

    Parameters
    ----------
    args: argparse.Namespace
        The arguments passed from the CLI. Run with `-h` to see the required parameters

    Returns
    -------
    None
    """
    build_cli_logger(
        "download_labels", log_to_file=not args.no_log, verbosity_level=args.verbose
    )
    api_token = parse_api_token(args.token_path)
    download_labels(
        args.slidescore_url,
        api_token,
        args.study_id,
        args.output_dir,
        output_type=args.output_type,
        question=args.question,
        email=args.user,
        disable_certificate_check=args.disable_certificate_check,
    )


def _write_shapely_to_disc(args: argparse.Namespace) -> None:
    write_shapely_to_disc(
        args.ann_file, str(args.study_id), args.ann_user, args.ann_label, args.ann_type
    )


def append_to_manifest(
    save_dir: pathlib.Path, image_id: int, filename: pathlib.Path
) -> None:
    """
    Create a manifest mapping image id to the filename.

    Parameters
    ----------
    save_dir : pathlib.Path
    image_id : int
    filename : pathlib.Path

    Returns
    -------
    None
    """
    with open(save_dir / "slidescore_mapping.txt", "a") as file:
        file.write(f"{image_id} {filename.name}\n")


def download_wsis(
    slidescore_url: str,
    api_token: str,
    study_id: int,
    save_dir: pathlib.Path,
    disable_certificate_check: bool = False,
) -> None:
    """
    Download all WSIs for a given study from SlideScore

    Parameters
    ----------
    slidescore_url : str
    api_token : str
    study_id : int
    save_dir : pathlib.Path
    disable_certificate_check : bool

    Returns
    -------
    None
    """
    logger.info(f"Will write to: {save_dir}")
    # Set up client and directories
    client = build_client(slidescore_url, api_token, disable_certificate_check)
    save_dir.mkdir(exist_ok=True)

    # Collect image metadata
    images = client.get_images(study_id)

    # Download and save WSIs
    for image in tqdm(images):
        image_id = image["id"]

        logger.info(f"Downloading image for id: {image_id}")
        filename = client.download_slide(study_id, image, save_dir=save_dir)
        logger.info(f"Image with id {image_id} has been saved to {filename}.")
        append_to_manifest(save_dir, image_id, filename)


def _download_wsi(args: argparse.Namespace):
    """Main function that downloads WSIs from SlideScore.

    Parameters
    ----------
    args: argparse.Namespace
        The arguments passed from the CLI. Run with `-h` to see the required parameters

    Returns
    -------
    None
    """
    # build_cli_logger("download_wsis", log_to_file=not args.no_log, verbosity_level=args.verbose)
    api_token = parse_api_token(args.token_path)
    download_wsis(
        args.slidescore_url,
        api_token,
        args.study_id,
        args.output_dir,
        disable_certificate_check=args.disable_certificate_check,
    )


def register_parser(parser: argparse._SubParsersAction):
    """Register slidescore commands to a root parser."""
    # Write annotations as shapely files to disc
    write_shapely_parser = parser.add_parser(
        "write-shapely",
        help="Given a slidescore annotation file, write shapely objects to disc",
    )
    write_shapely_parser.add_argument(
        "ann_file", type=pathlib.Path, help="Path to read text annotation file"
    )
    write_shapely_parser.add_argument(
        "ann_label", help="Name of the required class label", type=str
    )
    write_shapely_parser.add_argument(
        "ann_user",
        help="Email(-like) reference indicating submitted annotations on SlideScore.",
        type=str,
    )
    write_shapely_parser.add_argument(
        "ann_type",
        nargs="*",
        type=str,
        help="list of required type of annotations",
        default=["brush", "polygon"],
    )
    write_shapely_parser.set_defaults(subcommand=_write_shapely_to_disc)

    # Download slides to a subfolder
    download_wsi_parser = parser.add_parser(
        "download-wsis", help="Download WSIs from SlideScore."
    )
    download_wsi_parser.add_argument(
        "output_dir",
        type=pathlib.Path,
        help="Directory to save output too.",
    )

    download_wsi_parser.set_defaults(subcommand=_download_wsi)

    download_label_parser = parser.add_parser(
        "download-labels", help="Download labels from SlideScore."
    )
    download_label_parser.add_argument(
        "-q",
        "--question",
        dest="question",
        help="Question to save annotations for. If not set, will return all questions.",
        type=str,
        required=False,
    )
    download_label_parser.add_argument(
        "-u",
        "--user",
        dest="user",
        help="Email(-like) reference indicating submitted annotations on slidescore. "
        "If not set, will return questions from all users.",
        type=str,
        required=False,
    )
    download_label_parser.add_argument(
        "-o" "--output-type",
        dest="output_type",
        help="Type of output (AJEY IMPROVE THIS)",
        choices=LabelOutputType.__members__,
        default=LabelOutputType.shapely,
    )
    download_label_parser.add_argument(
        "output_dir",
        type=pathlib.Path,
        help="Directory to save output too.",
    )
    download_label_parser.set_defaults(subcommand=_download_labels)

    upload_label_parser = parser.add_parser(
        "upload-labels", help="Upload labels to SlideScore."
    )
    upload_label_parser.add_argument(
        "--csv-delimiter",
        type=str,
        help="The delimiter character used in the csv file.",
        default="\t",
    )
    upload_label_parser.add_argument(
        "-u",
        "--user",
        dest="user",
        help="Email(-like) reference indicating submitted annotations on SlideScore. "
        "If not set, will use the one included in the results file.",
        type=str,
        required=False,
    )
    upload_label_parser.add_argument(
        "--csv-fieldnames",
        nargs="*",
        type=str,
        default=["imageID", "imageName", "user", "question", "answer"],
    )
    upload_label_parser.add_argument(
        "-r",
        "--results-file",
        type=str,
        required=True,
        help="The results-file should be .csv file, separated with columns "
        "imageID, imageNumber, user, question, answer (or as given by --csv-fieldnames). "
        "User is the email(-like) address to register this "
        "upload as a unique entry, question is the type of cell (e.g.: lymphocytes, tumour cells) that "
        "pertains to the upload and answer contains a list of annotations (e.g.: ellipse, rectangle, polygon) "
        "to be uploaded to SlideScore. See the documentation for some examples.",
    )
    upload_label_parser.set_defaults(subcommand=_upload_labels)


def cli():
    """
    Console script for SlideScore API.
    """
    # From https://stackoverflow.com/questions/17073688/how-to-use-argparse-subparsers-correctly
    slidescore_parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    slidescore_parser.add_argument(
        "--slidescore-url",
        type=str,
        help="URL for SlideScore",
        default="https://slidescore.nki.nl/",
    )
    slidescore_parser.add_argument(
        "-t",
        "--token-path",
        dest="token_path",
        type=str,
        required=os.environ.get("SLIDESCORE_API_KEY", None) is None,
        help="Path to file with API token. Required if SLIDESCORE_API_KEY environment variable is not set. "
        "Will overwrite the environment variable if set.",
    )
    slidescore_parser.add_argument(
        "-s",
        "--study",
        dest="study_id",
        help="SlideScore Study ID",
        type=int,
        required=True,
    )
    slidescore_parser.add_argument(
        "--disable-certificate-check",
        help="Disable the certificate check.",
        action="store_true",
    )
    slidescore_parser.add_argument(
        "--no-log",
        help="Disable logging.",
        action="store_true",
    )
    slidescore_parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        help="Verbosity level, e.g. -v, -vv, -vvv",
        default=0,
    )

    slidescore_subparsers = slidescore_parser.add_subparsers(
        help="Possible SlideScore CLI utils to run."
    )
    slidescore_subparsers.required = True
    slidescore_subparsers.dest = "subcommand"

    # SlideScore related commands
    register_parser(slidescore_subparsers)

    args = slidescore_parser.parse_args()
    args.subcommand(args)


if __name__ == "__main__":
    cli()
