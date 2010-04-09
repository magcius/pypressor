#!/usr/bin/env python

import sys
import os
import urllib
import urllib2

try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO


COMPRESSIONS = {}
ENCODINGS    = {}

class noencode(object):
    DECODER = "%r"
    @staticmethod
    def encode(string):
        return string

    def decode(string):
        return string

class encodeencode(object):
    def __init__(self, encoding):
        self.encoding = encoding
        self.DECODER = "%%s.decode(%r)" % (self.encoding,)

    def encode(self, string):
        return string.encode(self.encoding)

    def decode(self, string):
        return string.decode(self.encoding)

none = COMPRESSIONS['none'] = COMPRESSIONS['no'] = COMPRESSIONS['n'] = noencode
bz2  = COMPRESSIONS['bz2']  = COMPRESSIONS['b'] = encodeencode("bz2")
zlib = COMPRESSIONS['zlib'] = COMPRESSIONS['z'] = encodeencode("zlib")

A85_CHARS = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ!#$%&()*+-;<=>?@^_`{|}~"

class ascii85(object):
    MODULES = "struct"
    DECODER = "''.join(struct.pack('<L',i)for i in[sum(c*85**i for i,c in enumerate(x))for x in(zip(*[iter(map(%r.find,%%r))]*5))])" % (A85_CHARS,)

    @staticmethod
    def encode(string):
        """
        Encode a string into its ascii85 counterpart.
        """
        for chunk in zip(*[iter(string)]*4):
            num = 0
            for i in string:
                num <<= 8
                num |= ord(i)
            encoded = ""
            while num:
                encoded += A85_CHARS[num%85]
                num /= 85
        return encoded

    @staticmethod
    def decode(string):
        """
        Decode an ascii85-encoded string into its original message.
        """
        for chunk in zip(*[iter(string)]*5):
            num = sum(A85_CHARS.find(c)*85**i for i, c in enumerate(chunk))
            decoded = ""
            while num:
                decoded += chr(num & 0xFF)
                num >>= 8
        return decoded[::-1]

ENCODINGS['none'] = ENCODINGS['no'] = ENCODINGS['n'] = noencode
base64   = ENCODINGS['base64']   = ENCODINGS['b64'] = ENCODINGS['b'] = encodeencode("base64")
uuencode = ENCODINGS['uuencode'] = ENCODINGS['uu']  = ENCODINGS['u'] = encodeencode("uuencode")
ENCODINGS['ascii85'] = ENCODINGS['a85'] = ENCODINGS['a'] = ascii85

class PasteProvider(object):
    """
    Abstract pastebin service provider. Subclasses should be able to paste text
    to a specific pastebin website and return the appropriate link
    
    TODO: add another cmdline option to specify paste website, add more paste
          providers
    """
    def __init__(self, url):
        self.url = url
    
    def paste(self, text):
        """
        Should return a string url to the paste.
        """

    def post(self, url, **params):
        """
        Makes a simple post request to a given url, returning the received
        data or None on an error
        """
        try:
            return urllib2.urlopen(self.url + url, urllib.urlencode(params)).read().strip()
        except urllib2.URLError, IOError:
            return None

class PastebincomProvider(PasteProvider):
    def paste(self, text):
        return self.post("/api_public.php", paste_code=text, paste_expire_date="N", paste_format="python")

class LodgeItProvider(PasteProvider):
    def __init__(self, url):
        super(LodgeItProvider, self).__init__(url)
        from xmlrpclib import ServerProxy
        self.proxy = ServerProxy(url+"/xmlrpc")

    def paste(self, text):
        return self.proxy.pastes.newPaste("python", text)

"""
class GistProvider(PasteProvider):
    def paste(self, text, private=False):
        out = {}

        out["file_ext[gistfile1]"] = ".py"
        out["file_contents[gistfile1]"] = text

        if private:
            out['private'] = 'on'

        out['login'] = os.popen('git config --global github.user').read().strip()
        out['token'] = os.popen('git config --global github.token').read().strip()

        url = 'http://gist.github.com/gists'
        data = urllib.urlencode(out)
        req = urllib2.Request(url, data)
        response = urllib2.urlopen(req)

        url = response.geturl()
        return url
"""

def compact_repr(elem):
    """
    A more compact version of repr for dicts and tuples
    that don't include whitespace for pretty formatting.

    We can't just repr(elem).replace(" ", "") because of
    spaces inside strings.
    """
    if isinstance(elem, dict):
        return "{" + ','.join("'%s':%s" % (k, compact_repr(v)) for k, v in elem.iteritems()) + "}"
    elif isinstance(elem, tuple):
        return "(" + ','.join(compact_repr(v) for v in elem) + ")"
    return repr(elem)

def pypressor(filenames, compression=bz2, encoding=base64, recursive=False, comment=True, shebang=True):
    """
    pypressor makes a self-extracting self-executable Python script
    that recreates the original filenames or folders.
    """
    def compress_string(string):
        """
        Compress a string and encode it to base64 if wanted.
        """
        return encoding.encode(compression.encode(string))

    def file_data(fn):
        """
        Get the file data for a specified filename "fn".
        """
        if fn == "-":
            cont = compress_string(sys.stdin.read())
            fn = "stdin"
        else:
            f = open(fn, "r")
            cont = compress_string(f.read())
            mode = os.stat(fn).st_mode
            f.close()
        return fn, mode, cont

    data = ""

    if shebang: data += "#!/usr/bin/env python\n"
    if comment: data += "# Please run this file with Python.\n"

    data += "import os\n"

    if len(filenames) == 1 and not os.path.isdir(filenames[0]):
        if not os.path.exists(filenames[0]):
            print "error: %r does not exist" % (filenames[0],)
            sys.exit(1)
        fn, mode, cont = file_data(filenames[0])
        data += ('n=%r\nf=open(n,"w")\nf.write('
                 "%s)\nf.close()\nos.chmod(n,%d)"
                 "" % (fn,
                 compression.DECODER % (encoding.DECODER % (cont,),), mode))
    else:
        files = {}
        needs_dirmach = False
        for filename in filenames:
            if not os.path.exists(filename):
                print "error: %r does not exist" % (filename,)
                sys.exit(1)
            elif os.path.isdir(filename):
                needs_dirmach = True
                if recursive:
                    context = files
                    L = len(os.path.dirname(filename))+1
                    for name, dirs, files in os.walk(filename):
                        name = name[L:]
                        context[name] = {}
                        oldcontext = context
                        context = context[name]
                        for file in files:
                            file, mode, cont = file_data(os.path.join(name, file))
                            context[name+'/'+file] = mode, cont
                        context = oldcontext
                else:
                    for file in os.listdir(filename):
                        file, mode, cont = file_data(os.path.join(filename, file))
                        files[os.path.basename(os.path.abspath(filename))+'/'+os.path.basename(file)] = mode, cont
            else:
                if os.path.basename(filename) != filename:
                    needs_dirmach = True
                filename, mode, cont = file_data(filename)
                files[filename] = mode, cont

        data += """D=%s
for n in D:
 d=D[n]""" % (compact_repr(files),)
        if needs_dirmach:
            data += """
 if isinstance(d,tuple):f=open(n,"w");f.write(%s);f.close();os.chmod(n,d[0])
 elif not os.path.exists(n):os.mkdir(n)"""
        else:
            data += """
 f=open(n,"w");f.write(%s);f.close();os.chmod(n,d[0)]"""
        data %= (compression.DECODER % (encoding.DECODER % ("d[1]",),),)
    return data

def main():
    from optparse import OptionParser
    opt = OptionParser(usage="%prog [options] filename1 filename2 ... filenameN")
    opt.add_option("-c", "--compression", action="store", metavar="COMPRESSION", default="bz2",
                   dest="compression", help="The compression algorithm to use. One of "
                   "'bz2', 'zlib', or 'none' [default: %default]")
    opt.add_option("-e", "--encodings", action="store", metavar="ENCODING", default="base64",
                   dest="encoding", help="The encoding algorithm to use. One of "
                   "'base64', 'uuencode', 'ascii85', 'none' [default: %default]")
    opt.add_option("--b64", "--no-base64", action="store_false", dest="base64",
                   default=True, help="Don't use base64 when outputting the compressed string")
    opt.add_option("-r", "--recursive", action="store_true", dest="recursive",
                   default=False, help="Recursively search folders to compress folders")
    opt.add_option("-I", "--inplace", action="store_true", dest="inplace",
                   default=False, help="Replace files inplace with their compressed versions")
    opt.add_option("--nc", "--no-comment", action="store_false", dest="comment",
                   default=True, help="Don't emit a comment in the compressed version")
    opt.add_option("--ns", "--no-shebang", action="store_false", dest="shebang",
                   default=True, help="Don't emit a shebang in the compressed version")
    opt.add_option("-p", "--paste", action="store_true", dest="paste",
                   default=False, help="Upload the final result to pastebin and print the link")
    options, filenames = opt.parse_args()
    if len(filenames) < 1:
        opt.print_help()
        print
        opt.error("need at least one filename")
    options.compression = COMPRESSIONS[options.compression]
    options.encoding    = ENCODINGS[options.encoding]
    if options.inplace:
        for fn in filenames:
            compressed = pypressor([fn], options.compression,
                           options.base64, options.recursive,
                           options.comment, options.shebang)
            f = open(fn, "w")
            f.write(compressed)
            f.close()
        return

    compressed = pypressor(filenames, options.compression,
                           options.base64, options.recursive,
                           options.comment, options.shebang)
    
    if options.paste:
        url = PastebincomProvider().paste(compressed)
        if url is not None:
            print url
            return
        print "Unable to paste result. Printing instead:"
        
    print compressed

if __name__ == "__main__":
    main()
