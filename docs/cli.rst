Command line tools
==================

The SlideScore API provides several command-line tools, all starting with :code:`slidescore <command>`. The documentation can
be found using :code:`slidescore --help`, or similarly by appending :code:`--help` to any of the subcommands.

SlideScore CLI
--------------
The SlideScore CLI tools require an API key, which can be set to the environmental variable
:code:`SLIDESCORE_API_KEY` (recommended) or through the flag :code:`-t token.txt`.

The following utilities to interact with SlideScore are implemented:

* :code:`slidescore download-wsi`: Download WSIs from SlideScore.
  This requires more permissions than most other API calls.
* :code:`slidescore download-labels`: Download labels from SlideScore.
* :code:`slidescore upload-labels`: Upload labels to SlideScore.
