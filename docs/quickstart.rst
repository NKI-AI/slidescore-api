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
  
  
First things first:

1. In order to use the slidescore API, you need to get an API key approved for a particular study/studies. You may reach out to Jan Hudecek (j.hudecek@nki.nl) and get this done. Once you have the API key, store it securely. **This is important because the API key can allow users to access proprietary data of the NKI and you do not want it in the wrong hands!**.

2. It is a good practice to export the API key to your working environment only when you plan to use the slidescore API. To do this, simply type in the following in your terminal - :bash:`export SLIDESCORE_API_KEY="your API key goes here"`.

3. You can also set the :bash:`-t` flag as the path to your API token while using the command line interface (CLI).

Note: You get access to only those slidescore studies which are assigned to you through the unique API key.

Now we are ready to use the API. Let us go through each functionality of the API.

1. **Download whole slide images from a study**
You can download all the whole slide images (WSIs) corresponding to a particular study from slidescore through the CLI. For clarity, you can easily check the help for this subcommand by typing :bash:`slidescore download-wsis -h`.

.. code-block:: console

   usage: slidescore download-wsis [-h] output_dir

   positional arguments:
     output_dir  Directory to save output too.

   optional arguments:
     -h, --help  show this help message and exit

If you have access to a slidescore study with id = *xyz* then you can download all the WSIs to a local folder *output_dir* on your computer with :bash:`slidescore -s xyz download-wsis output_dir`.
