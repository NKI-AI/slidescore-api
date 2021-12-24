.. role:: bash(code)
   :language: bash

Quick Start
===========
If the :doc:`/installation` went smoothly, you should be able to run :bash:`slidescore --help` and see:

.. code-block:: console

    usage: slidescore [-h] [--slidescore-url SLIDESCORE_URL] [-t TOKEN_PATH] -s STUDY_ID [--disable-certificate-check] {download-wsis,download-labels,upload-labels} ...

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
                            Path to file with API token. Required if SLIDESCORE_API_KEY environment variable is not set. Will overwrite the environment variable if set.
                            (default: None)
      -s STUDY_ID, --study STUDY_ID
                            SlideScore Study ID (default: None)
      --disable-certificate-check
                            Disable the certificate check. (default: False)
