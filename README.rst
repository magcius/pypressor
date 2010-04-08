=========
Pypressor
=========

*Pypressor* is a simple program that generates simple self-extracting
compression programs. It was based on an idea from Jon Morton, and
was originally designed for pasting binary files to pastebins.

Invocation
----------

To compress a single file, you can use::

    $ ./pypressor.py myfile.txt

To compress a folder (experimental), you can use::

    $ ./pypressor.py myfolder

To compress numerous files into one archive (experimental), you can use::

    $ ./pypressor.py file1.txt file2.txt

You can also read from STDIN::

    $ echo "My name is Inigo Montoya." | ./pypressor.py -

There's a bunch of other options::
    $ ./pypressor.py --help

    Usage: pypressor.py [options] filename1 filename2 ... filenameN

    Options:
      -h, --help          show this help message and exit
      -z, --zlib          Use zlib for compression
      -b, --bz2           Use bz2 for compression
      --b64, --no-base64  Don't use base64 when outputting the compressed string
      --nl, --no-newline  Strip newlines when outputting the base64 string
      -r, --recursive     Recursively search folders to compress folders
      -I, --inplace       Replace files inplace with their compressed versions
      --nc, --no-comment  Don't emit a comment in the compressed version
      --ns, --no-shebang  Don't emit a shebang in the compressed version

Conclusion
----------

Anyway, I hope this is somewhat useful to you guys.
