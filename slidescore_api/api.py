# coding=utf-8
# Copyright (c) slidescore_api contributors
"""Main module containing the SlideScore API wrapper."""

import io
import json
import logging
import pathlib
import re
import shutil
import sys
import urllib.parse
from typing import Dict, Iterable, List, Optional, Tuple, Union

import requests
from PIL import Image
from requests import Response
from tqdm import tqdm

type_to_name = [
    "FreeText",
    "Integer",
    "Real",
    "DropDown",
    "PositiveNegative",
    "Intensities",
    "Percentage",
    "Checkbox",
    "ClickFriendly",
    "PercentageOnly",
    "IntensitiesOnly",
    "PositiveNegativeOnly",
    "ClickFriendlyOnly",
    "ClickFriendlyPollOnly",
    "Explanation",
    "HScore",
    "HScoreOnly",
    "AnnoPoints",
    "AnnoMeasure",
    "AnnoShapes",
]


class SlideScoreResult:
    # pylint: disable=too-many-instance-attributes
    """Slidescore wrapper class for storing SlideScore server responses."""

    def __init__(self, slide_dict: Dict = None):
        """
        Parameters
        ----------
        slide_dict : dict
            SlideScore server response for annotations/labels.
        """

        self.__slide_dict = slide_dict
        if not slide_dict:
            slide_dict = {
                "imageID": 0,
                "imageName": "",
                "user": None,
                "tmaRow": None,
                "tmaCol": None,
                "tmaSampleID": None,
                "question": None,
                "answer": None,
                "lastModifiedOn": None,
            }

        self.image_id = int(slide_dict["imageID"])
        self.image_name = slide_dict["imageName"]
        self.user = slide_dict["user"]
        self.tma_row = int(slide_dict["tmaRow"]) if "tmaRow" in slide_dict else None
        self.tma_col = int(slide_dict["tmaCol"]) if "tmaCol" in slide_dict else None
        self.tma_sample_id = slide_dict["tmaSampleID"] if "tmaSampleID" in slide_dict else ""
        self.question = slide_dict["question"]
        self.answer = slide_dict["answer"]
        self.last_modified_on = slide_dict["lastModifiedOn"] if "lastModifiedOn" in slide_dict else ""

        self.points = None
        if self.answer is not None and self.answer[:2] == "[{":
            annos = json.loads(self.answer)
            if len(annos) > 0:
                if hasattr(annos[0], "type"):
                    self.annotations = annos
                else:
                    self.points = annos

    def to_row(self) -> str:
        """
        Convert dictionary output to a tab-separated string

        Returns
        -------
        str
            Tab separated string
        """
        if self.__slide_dict is None:
            return ""
        ret = str(self.image_id) + "\t" + self.image_name + "\t" + self.user + "\t"
        if self.tma_row is not None:
            ret = ret + str(self.tma_row) + "\t" + str(self.tma_col) + "\t" + self.tma_sample_id + "\t"
        ret = ret + self.question + "\t" + str(self.answer)  # + "\t"#  + self.last_modified_on
        return ret

    def __repr__(self):
        return (
            f"SlideScoreResult(image_id={self.image_id}, "
            f"image_name={self.image_name}, "
            f"user={self.user}, "
            f"tma_row={self.tma_row}, "
            f"tma_col={self.tma_col}, "
            f"tma_sample_id={self.tma_sample_id}, "
            f"question={self.question}, "
            f"answer=length {len(self.answer)})"
            f"lastModifiedOn={self.last_modified_on}, "
        )


class APIClient:
    """SlideScore API client."""

    def __init__(self, server: str, api_token: str, disable_cert_checking: bool = False) -> None:
        """
        Base client class for interfacing with slidescore servers.
        Needs and slidescore_url (example: "https://rhpc.nki.nl/slidescore/"), and a api token. Note the ending "/".

        Parameters
        ----------
        server : str
            Path to SlideScore server (without "Api/").
        api_token : str
            API token for this API request.
        disable_cert_checking : bool
            Disable checking of SSL certification (not recommended).
        """
        self.logger = logging.getLogger(type(self).__name__)

        self.server = server
        self.end_point = urllib.parse.urljoin(server, "Api/")
        self.api_token = api_token
        self.verify_certificate = not disable_cert_checking
        self.base_url: Union[str, None] = None
        self.cookie: Union[str, None] = None

    def perform_request(
        self,
        request: str,
        data: Optional[Dict],
        method: str = "POST",
        stream: bool = False,
    ) -> Response:
        """
        Base functionality for making requests to slidescore servers. Request should\
        be in the format of the slidescore API: https://www.slidescore.com/docs/api.html

        Parameters
        ----------
        request : str
        data : dict
        method : str
            HTTP request method (POST or GET).
        stream : bool

        Returns
        -------
        Response
        """
        if method not in ["POST", "GET"]:
            raise SlideScoreErrorException(f"Expected method to be either `POST` or `GET`. Got {method}.")

        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {self.api_token}",
        }
        url = urllib.parse.urljoin(self.end_point, request)

        if method == "POST":
            response = requests.post(url, verify=self.verify_certificate, headers=headers, data=data, timeout=60)
        else:
            response = requests.get(
                url,
                verify=self.verify_certificate,
                headers=headers,
                data=data,
                stream=stream,
                timeout=60,
            )
        if response.status_code != 200:
            response.raise_for_status()

        return response

    def get_images(self, study_id: int) -> Dict:
        """
        Get slide data (no slides) for all slides in the study.

        Parameters
        ----------
        study_id : int

        Returns
        -------
        dict
            Dictionary containing the images in the study.
        """
        response = self.perform_request("Images", {"studyid": study_id})
        rjson = response.json()
        self.logger.info("Found %s slides with SlideScore API for study ID %s.", len(rjson), study_id)

        return rjson

    def download_slide(
        self,
        study_id: int,
        image: dict,
        save_dir: pathlib.Path,
        skip_if_exists: bool = True,
    ) -> pathlib.Path:
        """
        Downloads a WSI from the SlideScore server, needs study_id and image.
        NOTE: this request has a different signature with different rights as the other
        methods and thus might require an api token with more rights than the other ones.

        Parameters
        ----------
        study_id : int
        image : dict
        save_dir : pathlib.Path
        skip_if_exists : bool

        Returns
        -------
        pathlib.Path
            Filename the output has been written to.

        """
        image_id = image["id"]
        filesize = image["fileSize"]
        response = self.perform_request(
            "DownloadSlide",
            {"studyid": study_id, "imageid": image_id},
            method="GET",
            stream=True,
        )

        raw = response.headers["Content-Disposition"]
        filename = self._get_filename(raw)
        self.logger.info("Writing to %s (reporting file size of %s)...", save_dir / filename, filesize)
        save_dir = save_dir / str(image_id)
        save_dir.mkdir(exist_ok=True)
        write_to = save_dir / filename
        history = self._read_from_history(save_dir)

        if skip_if_exists and str(filename) in history:
            self.logger.info("File %s already downloaded. Skipping.", save_dir / filename)
            response.close()
            return write_to

        temp_write_to = write_to.with_suffix(write_to.suffix + ".partial")

        with tqdm.wrapattr(
            open(temp_write_to, "wb"),
            "write",
            miniters=1,
            desc=str(filename),
            total=None,
        ) as file:
            for chunk in response.iter_content(chunk_size=4096):
                file.write(chunk)
        shutil.move(str(temp_write_to), str(write_to))

        self._write_to_history(save_dir, write_to.name)
        return write_to

    def get_results(self, study_id: int, **kwargs) -> Iterable[SlideScoreResult]:
        """
        Basic functionality to download all annotations made for a particular study.
        Returns a SlideScoreResult class wrapper containing the information.

        Parameters
        ----------
        study_id : int
            ID of SlideScore study.
        **kwargs: dict
            Dictionary with optional API flags. Check https://www.slidescore.com/docs/api.html#get-results for
            more details.

        Returns
        -------
        List[SlideScoreResult]
            List of SlideScore results.
        """
        optional_keys = ["question", "email", "imageid", "caseid"]
        if any(_ not in optional_keys for _ in kwargs):
            raise RuntimeError(f"Expected optional keys to be any of {', '.join(optional_keys)}. Got {kwargs.keys()}.")

        response = self.perform_request("Scores", {"studyid": study_id, **kwargs})
        rjson = response.json()
        for line in rjson:
            yield SlideScoreResult(line)

    def get_config(self, study_id: int) -> dict:
        """
        Get the configuration of a particular study. Returns a dictionary.

        Parameters
        ----------
        study_id : int
            ID of SlideScore study.

        Returns
        -------
        dict
        """
        response = self.perform_request("GetConfig", {"studyid": study_id})
        rjson = response.json()

        if not rjson["success"]:
            raise SlideScoreErrorException(f"Configuration for study id {study_id} not returned succesfully")

        return rjson["config"]

    def upload_results(self, study_id: int, results: List[SlideScoreResult]) -> bool:
        """
        Basic functionality to upload all annotations made for a particular study.
        Returns true if successful.

        results should be a list of strings, where each elemement is a line of text of the following format:
        imageID - tab - imageNumber - tab - author - tab - question - tab - annotatations
        annotations should be of the following format: a list of dicts containing annotation answers,
        converted to str format

        Parameters
        ----------
        study_id : int
        results : List[str]

        Returns
        -------
        bool
        """
        results_as_row = [r.to_row() for r in results]
        sres = "\n" + "\n".join(results_as_row)
        response = self.perform_request("UploadResults", {"studyid": study_id, "results": sres})
        rjson = response.json()
        if not rjson["success"]:
            raise SlideScoreErrorException(rjson["log"])
        return True

    def upload_asap(  # pylint: disable=R0913
        self,
        image_id: int,
        user: str,
        questions_map: Dict,
        annotation_name: str,
        asap_annotation: Dict,
    ) -> bool:
        """Upload annotations for study using ASAP functionality."""
        response = self.perform_request(
            "UploadASAPAnnotations",
            {
                "imageid": image_id,
                "questionsMap": "\n".join(key + ";" + val for key, val in questions_map.items()),
                "user": user,
                "annotationName": annotation_name,
                "asapAnnotation": asap_annotation,
            },
        )
        rjson = response.json()
        if not rjson["success"]:
            raise SlideScoreErrorException(rjson["log"])
        return True

    def get_image_metadata(self, image_id: int) -> dict:
        """
        Returns slide metadata for that image id.

        Parameters
        ----------
        image_id : int
            SlideScore Image ID.

        Returns
        -------
        dict
            Image metadata as stored in SlideScore.
        """
        response = self.perform_request("GetImageMetadata", {"imageId": image_id}, "GET")
        rjson = response.json()
        if not rjson["success"]:
            raise SlideScoreErrorException(rjson["log"])
        return rjson["metadata"]

    def export_asap(self, image_id: int, user: str, question: str) -> str:
        """Downloads ASAP annotations."""
        response = self.perform_request(
            "ExportASAPAnnotations",
            {"imageid": image_id, "user": user, "question": question},
        )
        rjson = response.json()
        if not rjson["success"]:
            raise SlideScoreErrorException(rjson["log"])
        rawresp = response.text
        if rawresp[0] != "<":
            raise RuntimeError("Incomplete XML ASAP output.")
        return rawresp

    def get_image_server_url(self, image_id: int) -> Tuple[str, str]:
        """
        Returns the image server slidescore url for given image.

        Parameters
        ----------
        image_id : int
            SlideScore Image ID.

        Returns
        -------
        tuple
            Pair consisting of url, cookie.
        """
        if self.base_url is None:
            raise RuntimeError

        response = self.perform_request(f"GetTileServer?imageId={str(image_id)}", None, method="GET")
        rjson: Dict = dict(response.json())
        url_parts = "/".join(["i", str(image_id), rjson["urlPart"], "_files"])
        return (
            urllib.parse.urljoin(self.base_url, url_parts),
            rjson["cookiePart"],
        )

    def set_cookie(self, image_id: int) -> None:
        """Set cookie; needed for getting deep zoomed tiles.

        Parameters
        ----------
        image_id : int
            SlideScore Image ID.
        """
        (self.base_url, self.cookie) = self.get_image_server_url(image_id)

    def get_tile(self, level: int, x_coord: int, y_coord: int) -> Image:
        """
        Gets tile from WSI for given magnification level.
        A WSI at any given magnification level is converted into an x by y tile matrix. This method downloads the tile
        at col (x) and row (y) only as jpeg. Maximum magnification level can be calculated as follows:
        max_level = int(np.ceil(math.log(max_dim, 2))), where max_dim is is the maximum of either height or width
        of the slide. This can be requested by calling get_image_metadata.

        Parameters
        ----------
        level : int
        x_coord : x
        y_coord : x

        Returns
        -------
        PIL.Image
            Requested tile.
        """
        if self.base_url is None:
            raise RuntimeError
        cookies: dict = {"t": self.cookie}
        response = requests.get(
            self.base_url + f"/{str(level)}/{str(x_coord)}_{str(y_coord)}.jpeg",
            stream=True,
            cookies=cookies,
            timeout=60,
        )
        if response.status_code == 200:
            return Image.open(io.BytesIO(response.content))
        raise SlideScoreErrorException(f"Expected response code 200. Got {response.status_code}.")

    @staticmethod
    def _get_filename(string: str) -> pathlib.Path:
        """
        Method to extract the filename from the HTTP header.
        Parameters
        ----------
        string : str
        Returns
        -------
        str
            Filename extracted from HTTP header.
        """
        filename_list = re.findall(r"filename\*?=([^;]+)", string, flags=re.IGNORECASE)
        filename: pathlib.Path = pathlib.Path(filename_list[0].strip().strip('"'))
        return filename

    @staticmethod
    def _write_to_history(save_dir: pathlib.Path, filename: Union[str, pathlib.Path]):
        with open(save_dir / ".download_history.txt", "a", encoding="utf-8") as file:
            file.write(f"{filename}\n")

    @staticmethod
    def _read_from_history(save_dir: pathlib.Path):
        history_filename = save_dir / ".download_history.txt"
        if not history_filename.is_file():
            return []

        with open(history_filename, "r", encoding="utf-8") as file:
            content = file.readlines()

        content = [_.strip() for _ in content]
        return content


class SlideScoreErrorException(Exception):
    """Class to hold a SlideScore exception."""


def build_client(slidescore_url: str, api_token: str, disable_certificate_check: bool = False) -> APIClient:
    """
    Build a SlideScore API Client.

    Parameters
    ----------
    slidescore_url: str
        Url of the slidescore server e.g.: https://rhpc.nki.nl/slidescore/ (without Api/).
    api_token: str
        SlideScore API token.
    disable_certificate_check : bool
        Disable HTTPS certificate check.

    Returns
    -------
    APIClient
        A SlideScore API client.
    """
    try:
        client = APIClient(slidescore_url, api_token, disable_cert_checking=disable_certificate_check)
    except requests.exceptions.SSLError as exception:
        sys.exit(
            f"SSLError, possibly because the SSL certificate cannot be read. "
            f"If you know what you are doing you can try --disable-certificate-check. "
            f"Full error: {exception}"
        )

    return client
