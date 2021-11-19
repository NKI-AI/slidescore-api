# coding=utf-8
# TODO: Parse function must be able to return None, and check before adding

import json
from pathlib import Path
from typing import Dict, Union

import numpy as np
from dlup import SlideImage
from PIL import Image, ImageDraw
from shapely.geometry import MultiPoint, MultiPolygon, Point, Polygon


def parse_brush_annotation(ann):
    # returns points: MultiPolygon
    positive_polygons = ann["positivePolygons"]
    negative_polygons = ann["negativePolygons"]
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
    used_negatives = {nidx: False for nidx in negative_polygons}
    inners_count = 0
    polygons = []
    for p_poly in positive_polygons.values():
        inners = []
        for nidx, n_poly in negative_polygons.items():
            if not used_negatives[nidx]:
                if n_poly.within(p_poly):
                    inners.append(n_poly)
                    used_negatives[nidx] = True
        inners_count += len(inners)
        polygon = Polygon(p_poly, inners)
        polygons.append(polygon)

    if not len(negative_polygons) == inners_count:
        print(
            f"WARNING: Not all negative_polygons accounted for: {inners_count} / {len(negative_polygons)}.\n"
            f"Indices :{[nidx for nidx, val in used_negatives.items() if not val]}.\n"
            f"Polygons:{[([pt for pt in negative_polygons[nidx].exterior.coords]) for nidx, val in used_negatives.items() if not val]}.\n"
            f"Areas   :{[negative_polygons[nidx].area for nidx, val in used_negatives.items() if not val]}.\n"
        )

    points = MultiPolygon(polygons)
    data = {
        "type": "brush",
        "points": points,
    }
    return data


def parse_polygon_annotation(ann):
    # returns points: MultiPolygon
    points = np.array([[pt["x"], pt["y"]] for pt in ann["points"]], dtype=np.float32)
    if len(points) < 3:
        print(f"WARNING: Invalid polygon: {ann}")
        points = []
    else:
        points = MultiPolygon([Polygon(points)])
    data = {
        "type": "polygon",
        "points": points,
    }
    return data


def parse_ellipse_annotation(ann):
    # returns center: Point, size: Point
    if (ann["center"]["x"] is not None) & (ann["center"]["y"] is not None):
        center = np.array([ann["center"]["x"], ann["center"]["y"]], dtype=np.float32)
        size = np.array([ann["size"]["x"], ann["size"]["y"]], dtype=np.float32)
        data = {
            "type": "ellipse",
            "center": Point(center),
            "size": Point(size),
        }
    else:
        print(f"WARNING: Invalid ellipse: {ann['center'], ann['size']}, adding as -1.")
        data = {
            "type": "ellipse",
            "center": Point(-1, -1),
            "size": Point(-1, -1),
        }
    return data


def parse_rect_annotation(ann):
    # returns corner: Point, size: Point
    corner = np.array([ann["corner"]["x"], ann["corner"]["y"]], dtype=np.float32)
    size = np.array([ann["size"]["x"], ann["size"]["y"]], dtype=np.float32)
    data = {
        "type": "rect",
        "corner": Point(corner),
        "size": Point(size),
    }
    return data


def parse_points_annotation(ann):
    # returns points: MultiPoint
    points = np.array([[_ann["x"], _ann["y"]] for _ann in ann], dtype=np.float32)
    data = {
        "type": "points",
        "points": MultiPoint(points),
    }
    return data


PARSE_FNS = {
    "brush": parse_brush_annotation,
    "ellipse": parse_ellipse_annotation,
    "polygon": parse_polygon_annotation,
    "rect": parse_rect_annotation,
    "points": parse_points_annotation,
}


def read_slidescore_annotations(fname: Union[str, Path], filter_empty=True) -> Dict[int, Dict]:
    """Function to convert slidescore annotations (txt file) to dictionary.
    Reads text file imported from slidescore into a dictionary with rows which are dicts with keys:
        row_idx: {imageID, slidename, author, label, data}
    NOTE: `row_idx` need not be sequential and is mapped to the original idx in the text file.
    Data is stored based on the type, accessed using `data["type"]`:
        brush: type (str), positive_polygons (ndarray) , negative_polygons (ndarray)
        polygon: type (str), points (ndarray)
        ellipse: type (str), center (ndarray) , size (ndarray)
    Empty rows have empty dict as data.
    """
    filepath = Path(fname)
    entries = filepath.read_text().split("\n")[:-1]
    num_entries = len(entries) - 1
    num_empty = 0

    headers = ["ImageID", "Image Name", "By", "Question", "Answer"]
    assert headers == entries[0].split("\t")

    rows = entries[1:]

    anns = {}
    for row_idx, row in enumerate(rows):
        _row = {k: v for k, v in zip(headers, row.split("\t"))}
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
                        data[idx] = PARSE_FNS[_ann["type"]](_ann)

                # Detection - Treat points as MultiPoint
                elif label_type == "detection":
                    data[0] = PARSE_FNS["points"](ann)

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

        anns[row_idx] = {
            "imageID": _row["ImageID"],
            "slidename": _row["Image Name"],
            "author": _row["By"],
            "label": _row["Question"],
            "data": data,
        }

    # Make sure we accounted for everything
    assert (
        num_entries == len(anns) + num_empty
    ), f"Some rows were missed. \nParsed: {len(anns) + num_empty}, Read: {num_entries}"

    return anns


def format_anns_for_db(anns):
    """Function to convert dictionary of slidescore annotations (dict) to rows for adding to database."""

    # Return var
    annotations = []

    # Process each row, can have multiple annotations
    for row in anns.values():
        annotation_base = {
            "author": row["author"],
            "source": "TCGA-BRCA",
            "slidename": row["slidename"],
            "slides_dir": "/home/x/data/TCGA-BRCA/slides",
        }
        data = row["data"]

        # Add each data as a separate db row
        for _data in data.values():
            _ann = {
                "label": row["label"],
                "gtype": None,
                "geom": None,
                "center_x": None,
                "center_y": None,
                "corner_x": None,
                "corner_y": None,
                "size_x": None,
                "size_y": None,
                "area": None,
                "rating": None,
                "comment": None,
                "version": None,
                "updated": None,
            }

            # Compute everything relevant and fill it in
            if _data["type"] in ["brush", "polygon"]:
                # Discard empty
                if len(_data["points"]) == 0:
                    continue
                x1, y1, x2, y2 = _data["points"].bounds
                _ann["gtype"] = "MULTIPOLYGON"
                _ann["geom"] = _data["points"]
                _ann["center_x"] = (x2 + x1) / 2
                _ann["center_y"] = (y2 + y1) / 2
                _ann["corner_x"] = x1
                _ann["corner_y"] = y1
                _ann["size_x"] = x2 - x1
                _ann["size_y"] = y2 - y1
                _ann["area"] = _ann["geom"].area

            elif _data["type"] == "rect":
                w, h = _data["size"].x, _data["size"].y
                x1, y1 = _data["corner"].x, _data["corner"].y
                x2, y2 = x1 + w, y1 + h
                _ann["gtype"] = "MULTIPOLYGON"
                _ann["geom"] = MultiPolygon([Polygon([[x1, y1], [x1, y2], [x2, y2], [x2, y1]])])
                _ann["center_x"] = (x2 + x1) / 2
                _ann["center_y"] = (y2 + y1) / 2
                _ann["corner_x"] = x1
                _ann["corner_y"] = y1
                _ann["size_x"] = x2 - x1
                _ann["size_y"] = y2 - y1
                _ann["area"] = _ann["geom"].area

            elif _data["type"] == "points":
                x1, y1, x2, y2 = _data["points"].bounds
                print(f"x1, y1, x2, y2: {x1, y1, x2, y2}")
                _ann["gtype"] = "MULTIPOINT"
                _ann["geom"] = _data["points"]
                _ann["center_x"] = (x2 + x1) / 2
                _ann["center_y"] = (y2 + y1) / 2
                _ann["corner_x"] = x1
                _ann["corner_y"] = y1
                _ann["size_x"] = x2 - x1
                _ann["size_y"] = y2 - y1
                _ann["area"] = len(_data["points"])

            elif _data["type"] == "ellipse":
                # NOTE: treating as rectangle
                w, h = _data["size"].x, _data["size"].y
                x0, y0 = _data["center"].x, _data["center"].y
                x1, y1 = x0 - w / 2, y0 - w / 2
                x2, y2 = x0 + w / 2, y0 + w / 2
                _ann["gtype"] = "MULTIPOLYGON"
                _ann["geom"] = MultiPolygon([Polygon([[x1, y1], [x1, y2], [x2, y2], [x2, y1]])])
                _ann["center_x"] = (x2 + x1) / 2
                _ann["center_y"] = (y2 + y1) / 2
                _ann["corner_x"] = x1
                _ann["corner_y"] = y1
                _ann["size_x"] = x2 - x1
                _ann["size_y"] = y2 - y1
                _ann["area"] = _ann["geom"].area

            elif _data["type"] == "comment":
                _ann["gtype"] = "COMMENT"
                _ann["comment"] = _data["text"]

            else:
                raise NotImplementedError(f'Unknown type: {_data["type"]}')

            # Convert to wkt
            if _ann["geom"] is not None:
                _ann["geom"] = _ann["geom"].wkt

            annotation = {**annotation_base, **_ann}
            annotations.append(annotation)

    return annotations


def generate_masks(path_to_slide, slidename, anns, author, mpp, classname, shape, visualize=False, validation=False):
    """Generate binary masks for annotated slidescore images using dlup
    Input Parameters
    1. path_to_slide --> This is the folder path where the .svs file is saved.
    2. slidename --> The anonymized name of the whole slide image
    3. anns --> A dictionary object containing all annotations of a study from slidescore
    4. scaling --> Desired scaling factor with respect to level 0 of WSI.
    5. classname --> The tissue class for which you want to generate the masks
    6. shape --> The shape of the annotation (one of brush, ellipse, polygon, rect, points)
    7. visualize --> Flag indicating if visualization of annotations is necessary. Default: False.
    Output
    1. A PIL image containing the binary mask (Image Mode -- "L")"""

    # TODO: Input a text file containing the image paths instead of parsing folder structure on the go.
    slide_image = SlideImage.from_file_path(path_to_slide)
    real_width, real_height = slide_image.size
    scaled_slide_image = slide_image.get_scaled_view(slide_image.get_scaling(mpp))
    scaled_width, scaled_height = scaled_slide_image.size
    histo_img = scaled_slide_image.read_region((0, 0), (int(scaled_width) - 1, int(scaled_height) - 1))
    histo_img = Image.fromarray(histo_img).convert("RGB")
    mask = Image.new("L", (scaled_width, scaled_height))
    if validation is False:
        mycoordslist = []
        for key in anns.keys():
            if anns[key]["author"] == author:
                if anns[key]["slidename"] == slidename:
                    if anns[key]["label"] == classname:
                        for i in range(len(anns[key]["data"])):
                            if anns[key]["data"][i]["type"] in shape:
                                if len(anns[key]["data"][i]["points"]) > 0:
                                    blob = [list(x.exterior.coords) for x in anns[key]["data"][i]["points"].geoms]
                                    if blob not in mycoordslist:
                                        mycoordslist.append(blob)

        polygons = []
        maskDraw = ImageDraw.Draw(mask)
        if len(mycoordslist) > 0:
            for element in mycoordslist:
                xy = []
                for coord in element[0]:
                    coord = list(coord)
                    coord[0] = coord[0] * scaled_width / real_width
                    coord[1] = coord[1] * scaled_height / real_height
                    coord = tuple(coord)
                    xy.append(coord)
                maskDraw.polygon(xy, fill=255)
                polygons.append(xy)

    if visualize:
        if validation is False:
            contour_draw = ImageDraw.Draw(histo_img)
            for polygon in polygons:
                contour_draw.polygon(polygon, outline="blue")
                mask.save(f"/home/a.karkala/mask.png")
        histo_img.save(f"/home/a.karkala/thumbnail.png")
    return mask, histo_img
