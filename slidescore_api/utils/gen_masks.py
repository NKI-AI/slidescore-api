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

def read_wsi(path_to_slide, mpp):
    """Read a WSI file from a given path string at a particular mpp resolution.

    Input:
        1. path_to_slide: String variable pointing to the path of WSI.
        2. mpp: The resolution at which the WSI must be read.

    Output:
        1. histo_img: The WSI image at the required mpp level as a PIL object (Image Mode -- "RGB")..
        2. real_dims: The dimensions of the WSI at full resolution.
        3. scaled_dims: The dimensions of the WSI after scaling to required mpp."""
    slide_image = SlideImage.from_file_path(Path(path_to_slide))
    real_dims = slide_image.size
    scaled_slide_image = slide_image.get_scaled_view(slide_image.get_scaling(mpp))
    scaled_dims = scaled_slide_image.size
    histo_img = scaled_slide_image.read_region((0, 0), (int(scaled_dims[0]) - 1, int(scaled_dims[1]) - 1))
    histo_img = histo_img.convert("RGB")
    return histo_img, scaled_dims, real_dims

def preprocess_anns(anns, label, author, ann_type):
    """Preprocess the slidescore annotation file for a study for faster access during training"""
    preprocessed_annotations = {}
    for key in anns.keys():
        if anns[key]["author"] == author:
            if anns[key]["label"] == label:
                for i in range(len(anns[key]["data"])):
                    if anns[key]["data"][i]["type"] in ann_type:
                        slide_name = anns[key]["slidename"]
                        preprocessed_annotations[slide_name] = {label: anns[key]["data"][i]["points"]}
    return preprocessed_annotations

def get_ann_coords(anns, ann_attr):
    """Get the coorinates for the points in the annotation files. Filter for annotation author, slide name, class label
       and type of Annotation.

    Input:
        1. anns: Dictionary object containing all the annotations from some slidescore study.
        2. ann_attr: Dictionary object containing the attributes of the annotations.

    Output:
        1. mycoordslist: A list containing all the annotation points for a particular class label by a particular author.
        """
    slidename = ann_attr["slidename"]
    label = ann_attr["classname"]
    mycoordslist = []
    if len(anns[slidename]) > 0:
        blob = [list(x.exterior.coords) for x in anns[slidename][label].geoms]
        if blob not in mycoordslist:
            mycoordslist.append(blob)
    return mycoordslist

def get_mask(coords, scaled_dims, real_dims):
    """Generate the annotation masks from the annotation points marked for a WSI.

    Input:
        1. coords: A list of annotation co-ordinates.
        2. scaled_dims: The dimensions of the WSI after scaling to required mpp.
        3. real_dims: The dimensions of the WSI at full resolution."""
    mask = Image.new("L", (scaled_dims[0], scaled_dims[1]))
    mask_draw = ImageDraw.Draw(mask)
    if len(coords) > 0:
        for element in coords:
            xy = []
            for coord in element[0]:
                coord = list(coord)
                coord[0] = coord[0] * scaled_dims[0] / real_dims[0]
                coord[1] = coord[1] * scaled_dims[1] / real_dims[1]
                coord = tuple(coord)
                xy.append(coord)
            mask_draw.polygon(xy, fill=255)
    return mask


def generate_masks(path_to_slide, slidename, anns, mpp, classname):
    """Generate binary masks for annotated slidescore images using dlup
    Input
        path_to_slide --> This is the folder path where the .svs file is saved.
        slidename --> The anonymized name of the whole slide image
        anns --> A dictionary object containing preprocessed annotations of a study from slidescore. 
        Use preprocess_anns() inside data.Dataset() class while initializing to preprocess the annotations.
        author --> Name of the author whose annotations are needed.
        mpp --> Desired mpp level to read the WSI.
        classname --> The class name for which you want to generate the masks (example: "specimen", "tumor" etc)
        shape --> The shape of the annotation (one of brush, ellipse, polygon, rect, points)
    Output
        A PIL image containing the whole slide image (Image Mode -- "RGB").
        A PIL image containing the binary mask (Image Mode -- "L")."""
    wsi, scaled_dims, real_dims = read_wsi(path_to_slide, mpp)
    coords = get_ann_coords(anns, {"slidename":slidename, "classname":classname})
    mask = get_mask(coords=coords, scaled_dims=scaled_dims, real_dims=real_dims)
    return mask, wsi
