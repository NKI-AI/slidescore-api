# SlideScore Python API
[![Tox](https://github.com/NKI-AI/slidescore-api/actions/workflows/tox.yml/badge.svg)](https://github.com/NKI-AI/slidescore-api/actions/workflows/tox.yml)
[![mypy](https://github.com/NKI-AI/slidescore-api/actions/workflows/mypy.yml/badge.svg)](https://github.com/NKI-AI/slidescore-api/actions/workflows/mypy.yml)
[![Pylint](https://github.com/NKI-AI/slidescore-api/actions/workflows/pylint.yml/badge.svg)](https://github.com/NKI-AI/slidescore-api/actions/workflows/pylint.yml)
[![Black](https://github.com/NKI-AI/slidescore-api/actions/workflows/black.yml/badge.svg)](https://github.com/NKI-AI/slidescore-api/actions/workflows/black.yml)

Utilities and command-line interface to interact with the [SlideScore](https://slidescore.com) API.

## Features
- Python SlideScore API client
- command-line utilities
  * For downloading from and uploading to SlideScore.


## Guide to using the slidescore API 
For uploading or downloading labels or whole-slide images, the following steps need to be undertaken:
- Contact Jan (j.hudecek@nki.nl) to obtain an API token which allows you to access the slidescore or rhpc server. You need to give the following information: study_id(s), upload download or both, server: slidescore or rhpc server on which the study is located
- Export the token to as an environment variable (every time you access our server) and also when you switch between accessing the slidescore or the rhpc-slidescore server : <pre><code> export SLIDESCORE_API_KEY=”your_token”</code></pre>
- use slidescore-api command

### Example command for uploading labels:
<pre><code> slidescore --slidescore-url "https://slidescore.nki.nl" --study "818"  --disable-certificate-check upload-labels --user "user_name@nki.nl" --results-file "path_to_file/file.csv" --csv-delimiter "," </code></pre>
- short flags do not work properly  at the moment) 
##### Requirements for the labels file:
- format: csv
- separator: default is tab “/t”.
- Every whole-slide image is one line.
- Csv columns are: "imageID", "imageName", "user", "question", "answer", however no header should be present in the annotation file.
- If you do not have the imageID or imageName the mapping for this can be copied on slidescore under: → study → export cases.
- imageID: type string
- imageName: type string
- question: type string    
  - Refers to the type of label, e.g. ducts or lymphocytes. 
  - This question needs to be added to the study on slidescore: go to →  study →  edit study →  questions →  select question type e.g. annotate shapes for bounding box →  name the question by clicking on it after it appears under "scoring sheet". The colour of the annotation can be also changed here.
- answer: type string 
  - Needs to be in a very specific format: “[{annotation 1}, {annotation 2}, {annotation n}]”. This list is inside the string.
  - It can be achieved with using json.dumps(wsi_results)
  - Every annotation is also in a specific format. 
    - For rectangle annotations: {"type": "rect", "corner": {"x": 123, "y": 456}, "size": {"x": 12, "y": 34}}. The corner coordinates refer to the top left corner of the rect. The size coordinates refer to the width (x) and the height (y). 
