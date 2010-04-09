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

There's a couple of neat encoding options to help save space. `ascii85`
is based on the April Fools RFC for encoding IP addresses. Since it's
not a codec included with Python, there will be some space taken up
dedicated to decoding it.

There's a bunch of other options::

    $ ./pypressor.py --help

    Options:
      -h, --help            show this help message and exit
      -c COMPRESSION, --compression=COMPRESSION
                            The compression algorithm to use. One of 'bz2',
                            'zlib', or 'none' [default: bz2]
      -e ENCODING, --encodings=ENCODING
                            The encoding algorithm to use. One of 'base64',
                            'uuencode', 'ascii85', 'none' [default: ascii85]
      -r, --recursive       Recursively search folders to compress folders
      -I, --inplace         Replace files inplace with their compressed versions
      --nc, --no-comment    Don't emit a comment in the compressed version
      --ns, --no-shebang    Don't emit a shebang in the compressed version
      -p, --paste           Upload the final result to pastebin and print the link

Conclusion
----------

Anyway, I hope this is somewhat useful to you guys.
