# coding=utf-8
# TODO: Parse function must be able to return None, and check before adding

import json
import os
import pickle
import warnings
from pathlib import Path
from typing import Dict, Union, List

import numpy as np
from shapely.geometry import MultiPoint, MultiPolygon, Point, Polygon, mapping

PathLike = Union[str, os.PathLike]


class SlideScoreAnnotations:
    headers = ["ImageID", "Image Name", "By", "Question", "Answer"]

    def __init__(self, filename: PathLike, study_id: str):
        self.filename = filename
        self.study_id = study_id
        self.__annotations = None

    @staticmethod
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

        # Check if any negative polygon is contained in a positive polygon
        # TODO: Should strike out inners already taken to make it efficient
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
                f"Polygons:{[([pt for pt in negative_polygons[idx].exterior.coords]) for nidx, val in used_negatives.items() if not val]}.\n"
                f"Areas   :{[negative_polygons[nidx].area for nidx, val in used_negatives.items() if not val]}.\n"
            )

        points = MultiPolygon(polygons)
        data = {
            "type": "brush",
            "points": points,
        }
        return data

    @staticmethod
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
        points = np.array([[pt["x"], pt["y"]] for pt in annotations["points"]], dtype=np.float32)
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

    @staticmethod
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

    @staticmethod
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

    @staticmethod
    def _parse_points_annotation(annotations: Dict) -> Dict:
        # returns points: MultiPoint
        points = np.array([[_ann["x"], _ann["y"]] for _ann in annotations], dtype=np.float32)
        data = {
            "type": "points",
            "points": MultiPoint(points),
        }
        return data

    def read_annotation_file(self):
        filepath = Path(self.filename)
        entries = filepath.read_text().split("\n")[:-1]
        num_entries = len(entries) - 1

        if not self.headers != entries[0].split("\t"):
            raise RuntimeError("Header is missing.")

        rows = entries[1:]
        return num_entries, rows

    def parse_annotations(self, filter_empty=True) -> None:
        """
        Function to convert slidescore annotations (txt file) to dictionary.

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
        filter_empty

        Returns
        -------

        """
        _parse_fns = {
            "brush": self._parse_brush_annotation,
            "ellipse": self._parse_ellipse_annotation,
            "polygon": self._parse_polygon_annotation,
            "rect": self._parse_rect_annotation,
            "points": self._parse_points_annotation,
        }

        num_empty = 0
        num_entries, rows = self.read_annotation_file()

        annotations = {}
        for row_idx, row in enumerate(rows):
            _row = {k: v for k, v in zip(self.headers, row.split("\t"))}
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
                            data[idx] = _parse_fns[_ann["type"]](_ann)

                    # Detection - Treat points as MultiPoint
                    elif label_type == "detection":
                        data[0] = _parse_fns["points"](ann)

                    else:
                        raise NotImplementedError(f"label_type ( {label_type} ) not implemented.")

                elif filter_empty:
                    num_empty += 1
                    continue

            except json.decoder.JSONDecodeError:
                if len(_row["Answer"]) > 0:
                    data = {0: {"type": "comment", "text": _row["Answer"]}}
                elif filter_empty:
                    continue

            annotations[row_idx] = {
                "imageID": _row["ImageID"],
                "slidename": _row["Image Name"],
                "author": _row["By"],
                "label": _row["Question"],
                "data": data,
            }

        # Make sure we accounted for everything
        if num_entries != len(annotations) + num_empty:
            raise RuntimeError(f"Some rows were missed. \nParsed: {len(annotations) + num_empty}, Read: {num_entries}")

        self.__annotations = annotations

    def save_shapely(self, label: str, author: str, ann_type: List):
        if self.__annotations is None:
            raise RuntimeError(f"Cannot save to shapely. First parse the annotations using `parse_annotations()`.")
        annotations = self.__annotations
        for key in annotations.keys():
            if annotations[key]["author"] == author and annotations[key]["label"] == label:
                slide_name = annotations[key]["slidename"]
                save_path = Path(self.study_id) / "annotations" / slide_name
                save_path.mkdir(parents=True, exist_ok=True)
                with open(save_path / (label + ".json"), "w") as file:
                    for idx in range(len(annotations[key]["data"])):
                        if annotations[key]["data"][idx]["type"] in ann_type and len(annotations[key]["data"][idx]["points"]) > 0:
                            json.dump(mapping(annotations[key]["data"][idx]["points"]), file, indent=2)

    @staticmethod
    def filter_annotations(annotations: Dict, label, author, ann_type) -> Dict:
        preprocessed_annotations = {}
        for key in annotations.keys():
            if annotations[key]["author"] == author and annotations[key]["label"] == label:
                slide_name = annotations[key]["slidename"]
                preprocessed_annotations[slide_name] = {}
                preprocessed_annotations[slide_name][annotations[key]["label"]] = {}
                for i in range(len(annotations[key]["data"])):
                    if (
                        annotations[key]["data"][i]["type"] in ann_type
                        and len(annotations[key]["data"][i]["points"]) > 0
                    ):
                        preprocessed_annotations[slide_name][label][i] = annotations[key]["data"][i]["points"]
        return preprocessed_annotations

    @staticmethod
    def get_annotation_coordinates(annotations, ann_attr, save=False):
        """Get the coorinates for the points in the annotation files. Filter for annotation author, slide name, class label
           and type of Annotation.

        Input:
            1. anns: Dictionary object containing all the annotations from some slidescore study.
            2. ann_attr: Dictionary object containing the attributes of the annotations.

        Output:
            1. mycoordslist: A list containing all the annotation points for a particular class label by a particular author.
        """
        coordinates = []
        if annotations is not None:
            slidename = ann_attr["slidename"]
            label = ann_attr["classname"]
            blob = []
            for idx in range(len(annotations[slidename][label])):
                blob.append([list(x.exterior.coords) for x in annotations[slidename][label][idx].geoms])
            if blob not in coordinates:
                coordinates.append(blob)
            if save:
                file = open(slidename + ".pkl", "wb")
                pickle.dump(coordinates, file)
                file.close()
        return coordinates


if __name__ == "__main__":
    reader = SlideScoreAnnotations(Path("/Users/jteuwen/Downloads/TISSUE_COMPARTMENTS_21_12_20_48.txt"), "465")
    reader.parse_annotations()
    reader.save_shapely(label="specimen", author="a.karkala@nki.nl", ann_type=["brush", "polygon"])
