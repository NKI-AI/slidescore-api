#!/home/ajey/miniconda3/bin/python3
# coding=utf-8
"""Utility file containing parsing modules and functions to save slidescore annotations."""

import json
import warnings
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Iterable, NamedTuple, Union

import numpy as np
from shapely.geometry import MultiPoint, MultiPolygon, Point, Polygon, mapping


class ImageAnnotation(NamedTuple):
    """
    NamedTuple class for Image Annotations.

    This class can be instantiated to contain different attributes of a WSI along with its annotations.
    """

    slide_name: str
    author: str
    label: str
    annotation: Union[
        Dict[int, Union[dict, Any]],
        Dict[int, Union[Union[Dict[str, Union[str, Any]], dict], Any]],
    ]


class AnnotationType(Enum):
    """
    Enumerated class for type of slidescore annotations
    """

    POLYGON: str = "polygon"
    RECT: str = "rect"
    ELLIPSE: str = "ellipse"
    BRUSH: str = "brush"
    HEATMAP: str = "heatmap"
    POINTS: str = "points"


def _check_type_error(filter_type: list) -> None:
    for f_type in filter_type:
        if f_type.upper() not in list(AnnotationType.__members__):
            raise TypeError(f"Annotation type {f_type} is not supported.")


def save_shapely(annotations: ImageAnnotation, save_dir: Path, filter_type: list) -> None:
    """
    Given a single Annotation of a WSI, this function writes them as shapely objects to disc
    Parameters
    ----------
    annotations: ImageAnnotation
        A named Tuple containing Image annotations

    save_dir: Path
        A Path object pointing to the directory where the shapely objects need to be written.

    filter_type: list
        List of annotation types that is to be written to disc. members must be enumerated in AnnotationType

    Returns
    ----------
    None
    """
    _check_type_error(filter_type)
    save_path = save_dir / "annotations" / annotations.author / annotations.slide_name
    save_path.mkdir(parents=True, exist_ok=True)
    with open(save_path / (annotations.label + ".json"), "w", encoding="utf-8") as file:
        dump_list: list = []
        for polygon_id, _ in enumerate(annotations.annotation):
            # Handles only polygon and brush type annotations.
            if (
                AnnotationType[annotations.annotation[polygon_id]["type"].upper()] == AnnotationType.POLYGON
                or AnnotationType[annotations.annotation[polygon_id]["type"].upper()] == AnnotationType.BRUSH
            ):
                if len(annotations.annotation[polygon_id]["points"]) > 0:
                    dump_list.append(mapping(annotations.annotation[polygon_id]["points"]))
        json.dump(dump_list, file, indent=2)


def _parse_brush_annotation(annotations: Dict) -> Dict:
    """

    Parameters
    ----------
    annotations : dict

    Returns
    -------
    dict
        Dictionary with key type: "brush" and "points" a shapely.geometry.MultiplePolygon
    """
    positive_polygons = annotations["positivePolygons"]
    negative_polygons = annotations["negativePolygons"]
    positive_polygons = {
        k: Polygon(np.array([[pt["x"], pt["y"]] for pt in polygon], dtype=np.float32))
        for k, polygon in enumerate(positive_polygons)
    }
    negative_polygons = {
        k: Polygon(np.array([[pt["x"], pt["y"]] for pt in polygon], dtype=np.float32))
        for k, polygon in enumerate(negative_polygons)
    }

    used_negatives = {idx: False for idx in negative_polygons}
    inners_count = 0
    polygons = []
    for p_poly in positive_polygons.values():
        inners = []
        for idx, n_poly in negative_polygons.items():
            if not used_negatives[idx]:
                if n_poly.within(p_poly):
                    inners.append(n_poly)
                    used_negatives[idx] = True
        inners_count += len(inners)
        polygon = Polygon(p_poly, inners)
        polygons.append(polygon)

    if not len(negative_polygons) == inners_count:
        warnings.warn(
            f"Not all negative_polygons accounted for: {inners_count} / {len(negative_polygons)}.\n"
            f"Indices :{[nidx for nidx, val in used_negatives.items() if not val]}.\n"
            f"Polygons:"
            f"{[list(negative_polygons[idx].exterior.coords) for idx, val in used_negatives.items() if not val]}.\n"
            f"Areas   :{[negative_polygons[nidx].area for nidx, val in used_negatives.items() if not val]}.\n"
        )

    points = MultiPolygon(polygons)
    data = {
        "type": "brush",
        "points": points,
    }
    return data


def _parse_polygon_annotation(annotations: Dict) -> Dict:
    """

    Parameters
    ----------
    annotations : dict

    Returns
    -------
    dict
        Dictionary with key type: "brush" and "points" a shapely.geometry.MultiplePolygon
    """
    # returns points: MultiPolygon
    points: Any = np.array([[pt["x"], pt["y"]] for pt in annotations["points"]], dtype=np.float32)
    if len(points) < 3:
        warnings.warn(f"Invalid polygon: {annotations}")
        points = []
    else:
        points = MultiPolygon([Polygon(points)])
    data = {
        "type": "polygon",
        "points": points,
    }
    return data


def _parse_ellipse_annotation(annotations: Dict) -> Dict:
    # returns center: Point, size: Point
    if (annotations["center"]["x"] is not None) & (annotations["center"]["y"] is not None):
        center = np.array([annotations["center"]["x"], annotations["center"]["y"]], dtype=np.float32)
        size = np.array([annotations["size"]["x"], annotations["size"]["y"]], dtype=np.float32)
        data = {
            "type": "ellipse",
            "center": Point(center),
            "size": Point(size),
        }
    else:
        warnings.warn(f"Invalid ellipse: {annotations['center'], annotations['size']}, adding as -1.")
        data = {
            "type": "ellipse",
            "center": Point(-1, -1),
            "size": Point(-1, -1),
        }
    return data


def _parse_rect_annotation(annotations: Dict) -> Dict:
    # returns corner: Point, size: Point
    corner = np.array([annotations["corner"]["x"], annotations["corner"]["y"]], dtype=np.float32)
    size = np.array([annotations["size"]["x"], annotations["size"]["y"]], dtype=np.float32)
    data = {
        "type": "rect",
        "corner": Point(corner),
        "size": Point(size),
    }
    return data


def _parse_points_annotation(annotations: Dict) -> Dict:
    # returns points: MultiPoint
    points = np.array([[_ann["x"], _ann["y"]] for _ann in annotations], dtype=np.float32)
    data = {
        "type": "points",
        "points": MultiPoint(points),
    }
    return data


class SlideScoreAnnotations:
    """
    Main class for Slidescore annotation parsing.
    """

    _headers = ["ImageID", "Image Name", "By", "Question", "Answer"]
    _parse_fns = {
        "brush": _parse_brush_annotation,
        "ellipse": _parse_ellipse_annotation,
        "polygon": _parse_polygon_annotation,
        "rect": _parse_rect_annotation,
        "points": _parse_points_annotation,
    }

    def __init__(self):
        self.unannotated = 0
        self.annotations_generated = 0
        self.num_empty = 0
        self.num_entries = 0
        self._annotated_images = []
        self._row_iterator = None

    def check(self) -> None:
        """
        Performs Sanity checking while reading annotations from manually downloaded annotations.

        Returns
        -------
        None
        """
        # Make sure we accounted for everything
        if self.num_entries != self.annotations_generated + self.unannotated + self.num_empty:
            raise RuntimeError(
                f"Some rows were missed. \nParsed: {self.annotations_generated + self.num_empty}, "
                f"Read: {self.num_entries} "
            )
        print("Total annotated images: ", self.annotations_generated)
        print("Total unannotated images: ", self.unannotated)
        print("Total empty entries: ", self.num_empty)

    def annotation_file_iterator(self, filename: Path) -> Iterable:
        """
        Generator function to yield a single line from a manually downloaded slidescore annotation file.

        Parameters
        ----------
        filename: Path
            The path to the slidescore annotation file.

        Returns
        -------
        line: Iterable
            One line from the annotation file.
        """
        with open(filename, "r", encoding="utf-8") as annotation_file:
            if self._headers != annotation_file.readline().strip().split("\t"):
                raise RuntimeError("Header missing.")
            for line in annotation_file:
                self._row_iterator = line
                yield self._row_iterator

    def _parse_annotation_row(self, row, filter_empty):  # pylint:disable=too-many-branches
        _row = dict(zip(self._headers, row.split("\t")))
        data = {}
        try:
            ann = json.loads(_row["Answer"])
            if len(ann) > 0:
                # Points dont have type, only x,y; so we use that to distinguish task
                # Code can be shortened, but is more readable this way
                if "type" in ann[0]:
                    label_type = "segmentation"
                else:
                    label_type = "detection"

                # Segmentation - Treat brush, polygon as MultiPolygon
                if label_type == "segmentation":
                    for idx, _ann in enumerate(ann):
                        data[idx] = self._parse_fns[_ann["type"]](_ann)

                # Detection - Treat points as MultiPoint
                elif label_type == "detection":
                    data[0] = self._parse_fns["points"](ann)

                else:
                    raise NotImplementedError(f"label_type ( {label_type} ) not implemented.")

            elif filter_empty:
                return None

        except json.decoder.JSONDecodeError:
            if len(_row["Answer"]) > 0:
                data = {0: {"type": "comment", "text": _row["Answer"]}}
            elif filter_empty:
                return None

        return _row, data

    @property
    def annotated_images_list(self) -> list:
        """
        Get a list of all annotated images from a given slidescore study

        Returns
        -------
        list of all slide names that are annotated in a slidescore study
        """
        for line in self.from_iterable(self._row_iterator):
            self._annotated_images.append(line.slide_name)
        self.unannotated = 0
        self.annotations_generated = 0
        return self._annotated_images

    def from_iterable(
        self,
        row_iterator: Iterable,
        filter_author: str = None,
        filter_label: str = None,
        filter_empty=True,
    ) -> Iterable:
        """
        Function to convert slidescore annotations (txt file) to an iterable.

        Reads text file imported from slidescore into a dictionary with rows which are dicts with keys:
            row_idx: {imageID, slidename, author, label, data}

        Notes
        -----
        `row_idx` need not be sequential and is mapped to the original idx in the text file.
        Data is stored based on the type, accessed using `data["type"]`:
            brush: type (str), positive_polygons (ndarray) , negative_polygons (ndarray)
            polygon: type (str), points (ndarray)
            ellipse: type (str), center (ndarray) , size (ndarray)
        Empty rows have empty dict as data.

        Parameters
        ----------
        row_iterator: Iterable
            An iterable object that holds a single row of annotations and attributes.
        filter_empty: bool
            A binary flag to indicate whether or not empty rows must be filtered.
        filter_author: str
            Email-like string to look for annotations corresponding to a particular annotation author.
        filter_label:
            a string that indicates a label name in the slidescore study deemed necessary by the user.

        Returns
        -------
        row_annotation: ImageAnnotation
            A named tuple containing the attributes and annotations of a single WSI.
        """
        for row in row_iterator:
            _return = self._parse_annotation_row(row, filter_empty=filter_empty)
            if _return is None:
                self.num_empty += 1
                continue
            _row, data = _return

            row_annotation = ImageAnnotation(
                slide_name=_row["Image Name"],
                author=_row["By"],
                label=_row["Question"],
                annotation=data,
            )

            if filter_author is not None or filter_label is not None:
                if row_annotation.author != filter_author or row_annotation.label != filter_label:
                    self.unannotated += 1
                    continue
            self.annotations_generated += 1

            yield row_annotation
