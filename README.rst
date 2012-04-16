=======
Signpic
=======

A small script to sign your JPEG pictures.

To install::

    pip install signpic

To use it, run **signpic**::

    $ signpic --help
    usage: signpic [-h] [--signature SIGNATURE] [--debug] [--phose] pic

    Sign some pictures.

    positional arguments:
    pic                   Directory or single picture.

    optional arguments:
    -h, --help            show this help message and exit
    --signature SIGNATURE
                            Signature file. If not given, will look at
                            ~/.signature.jpg then fallback to the included
                            signature.
    --debug               Debug mode
    --phose               Use Powerhose
