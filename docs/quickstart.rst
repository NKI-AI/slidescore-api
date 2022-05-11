.. role:: bash(code)
   :language: bash

Quick Start
===========
If the :doc:`/installation` went smoothly, you should be able to run :bash:`slidescore --help` and see:

.. code-block:: console

   usage: slidescore [-h] [--slidescore-url SLIDESCORE_URL] -t TOKEN_PATH -s STUDY_ID [--disable-certificate-check] [--no-log] [-v] {download-wsis,download-labels,upload-labels}           ...

      positional arguments:
        {download-wsis,download-labels,upload-labels}
                              Possible SlideScore CLI utils to run.
          download-wsis       Download WSIs from SlideScore.
          download-labels     Download labels from SlideScore.
          upload-labels       Upload labels to SlideScore.

      optional arguments:
        -h, --help            show this help message and exit
        --slidescore-url SLIDESCORE_URL
                              URL for SlideScore (default: https://slidescore.nki.nl/)
        -t TOKEN_PATH, --token-path TOKEN_PATH
                              Path to file with API token. Required if SLIDESCORE_API_KEY environment variable is not set. Will overwrite the environment variable if set.                                     (default: None)
        -s STUDY_ID, --study STUDY_ID
                              SlideScore Study ID (default: None)
        --disable-certificate-check
                              Disable the certificate check. (default: False)
        --no-log              Disable logging. (default: False)
        -v, --verbose         Verbosity level, e.g. -v, -vv, -vvv (default: 0)


Setting things up with the API key
==================================
In order to use the slidescore API, you need to get an API key approved for a particular study/studies. You may reach out to Jan Hudecek (j.hudecek@nki.nl) and get this done. Once you have the API key, store it securely. **This is important because the API key can allow users to access proprietary data of the NKI and you do not want it in the wrong hands!**

1. It is a good practice to export the API key to your working environment only when you plan to use the slidescore API.
2. While using the slidescore-api in your python programs, set an environment variable - :bash:`export SLIDESCORE_API_KEY="your API key goes here"`.
3. While using the command line interface (CLI), the environment variable can be set in a similar manner or simply set the :bash:`-t` flag as the path to your API token.

Note: You get access to only those slidescore studies which are assigned to you through the unique API key.

Now we are ready to use the API. Let us go through each functionality of the API.

Command Line Interface
=======================

CLI cheat sheet
-----------------
   1. To download WSIs to a folder:

      :bash:`slidescore -s xyz download-wsis output_dir`


   2. To download annotations (of type BRUSH and POLYGON) from a study in Shapely format:

      :bash:`slidescore -s xyz download-labels -o SHAPELY -q label_name BRUSH POLYGON output_dir`

Download whole slide images of a slidescore study
--------------------------------------------------------

   1. You can download all the whole slide images (WSIs) corresponding to a particular study from slidescore through the CLI.
   2. For clarity, you can easily check the help for this subcommand by typing :bash:`slidescore download-wsis -h`

.. code-block:: console

   usage: slidescore download-wsis [-h] output_dir

   positional arguments:
     output_dir  Directory to save output too.

   optional arguments:
     -h, --help  show this help message and exit

**If you have access to a slidescore study with id = *xyz* then you can download all the WSIs to a local folder *output_dir* on your computer with:**

                              :bash:`slidescore -s xyz download-wsis output_dir`

Download annotations for WSIs of a slidescore study
------------------------------------------------------------

   1. This is an important feature of the slidescore-api. For quick and efficient handling of data annotations, you can download and store them to your computer in different formats. This avoids extra coding effort while developing your deep learning models as the slidescore-api neatly organises the necessary annotations for you.
   2. Look at the help of this subcommand using - :bash:`slidescore download-labels -h`

.. code-block:: console

   usage: slidescore download-labels [-h] [-q QUESTION] [-u USER] [-o--output-type {JSON,RAW,SHAPELY}] [ann_type ...] output_dir

   positional arguments:
     ann_type              list of required type of annotations
     output_dir            Directory to save output too.

   optional arguments:
     -h, --help            show this help message and exit
     -q QUESTION, --question QUESTION
                           Question to save annotations for. If not set, will return all questions.
     -u USER, --user USER  Email(-like) reference indicating submitted annotations on slidescore. If not set, will return questions from all users.
     -o--output-type {JSON,RAW,SHAPELY}
                           Type of output

Positional Arguments:

1. :bash:`ann_type` - While annotating on slidescore, users choose different annotation types. One from "POLYGON", "BRUSH", "RECT", "ELLIPSE" and "HEATMAP"
2. :bash:`output_dir` - Path to the directory where the labels need to be downloaded.

Optional Arguments:

1. Set the :bash:`-q` flag to download the annotations for a particular question of your choice. It could be a training label like "tumor", "blood vessels", "ducts" etc.
2. Set the :bash:`-u` flag to download the annotations corresponding to a particular user involved in the study.
3. Set the :bash:`-o` flag to write the downloaded annotations in a particular format. Choose one from "JSON", "RAW", "SHAPELY".

**If you have access to a slidescore study with id = *xyz* then you can download the annotations by all authors corresponding to a label *label_name* as :bash:`SHAPELY` objects to a local folder *output_dir* on your computer with:**

                           :bash:`slidescore -s xyz download-labels -o SHAPELY -q label_name BRUSH POLYGON output_dir`
