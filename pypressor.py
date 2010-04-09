#!/usr/bin/env python

import sys
import os
import urllib
import urllib2
import string

try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO


COMPRESSIONS = {}
ENCODINGS    = {}

class noencode(object):
    @staticmethod
    def encode(string):
        return string

    @staticmethod
    def get_dependencies(string, multi=False):
        return "", "", ""

    @staticmethod
    def decode(string):
        return string

class encodeencode(object):
    def __init__(self, encoding, newlines=False):
        self.encoding = encoding
        self.newlines = newlines

    def encode(self, string):
        string = string.encode(self.encoding)
        if self.newlines:
            string = string.replace("\n", "")
        return string

    def get_dependencies(self, string, multi=False):
        return "", "", "%%s.decode(%r)" % (self.encoding,)

    def decode(self, string):
        return string.decode(self.encoding)

none = COMPRESSIONS['none'] = COMPRESSIONS['no'] = COMPRESSIONS['n'] = noencode
bz2  = COMPRESSIONS['bz2']  = COMPRESSIONS['b'] = encodeencode("bz2")
zlib = COMPRESSIONS['zlib'] = COMPRESSIONS['z'] = encodeencode("zlib")

A85_CHARS = string.digits+string.ascii_letters+"!#$%&()*+-;<=>?@^_`{|}~"

class ascii85(object):
    HEADER1 = """def D(S,d=''):
 for c in zip(*[iter(S)]*5):
  if c[0]==',':d+='\\0'*int(''.join(c[1:]),16);continue
  n=sum((s.digits+s.ascii_letters+'!#$%&()*+-;<=>?@^_`{|}~').find(x)*85**i for i,x in enumerate(c))
  while n:d+=chr(n&255);n>>=8
 return d
"""
    DECODER1 = "D(%s)"
    DECODER2 = "''.join(struct.pack('>L',i)for i in[sum(c*85**i for i,c in enumerate(x))for x in(zip(*[iter(map((s.digits+s.ascii_letters+'!#$%%&()*+-;<=>?@^_`{|}~').find,%s))]*5))])"

    @staticmethod
    def encode(string):
        """
        Encode a string into its ascii85 counterpart.
        """
        encoded = []
        chunks = zip(*[iter(string)]*4)
        leftover = len(string) & 3
        if leftover:
            chunks.append(tuple(string[-leftover:]))
 
        for chunk in chunks:
            if chunk == ("\0",)*len(chunk):
                new0len = 0
                if encoded and encoded[-1][0] == ",":
                    new0len = len(chunk)+int(encoded[-1][1:],16)
                if 0 < new0len <= 0xFFFF:
                    encoded[-1] = ",%04x" % (new0len,)
                else:
                    encoded.append(",%04x" % (len(chunk),))
                continue
 
            num = 0
            for i in chunk[::-1]:
                num <<= 8
                num  |= ord(i)
            S = ""
            for i in reversed(xrange(5)):
                S += A85_CHARS[num%85]
                num /= 85
            encoded.append(S)
            num = 0
            while chunk[-1] == "\0":
                num += 1
                chunk = chunk[:-1]
            if num:
                encoded.append(",%04x" % (num,))
        return ''.join(encoded)

    @classmethod
    def get_dependencies(c, string, multi=False):
        if "," in string or multi:
            return ",string as s", c.HEADER1, c.DECODER1
        return ",struct,string as s", "", c.DECODER2

    @staticmethod
    def decode(string):
        """
        Decode an ascii85-encoded string into its original message.
        """
        decoded = ""
        for chunk in zip(*[iter(string)]*5):
            if chunk[0] == ",":
                decoded += "\0"*int(''.join(chunk[1:]),16)
            else:
                num = sum(A85_CHARS.find(c)*85**i for i, c in enumerate(chunk))
                while num:
                    decoded += chr(num & 0xFF)
                    num >>= 8
        return decoded

ENCODINGS['none'] = ENCODINGS['no'] = ENCODINGS['n'] = noencode
base64   = ENCODINGS['base64']   = ENCODINGS['b64'] = ENCODINGS['b'] = encodeencode("base64", True)
uuencode = ENCODINGS['uuencode'] = ENCODINGS['uu']  = ENCODINGS['u'] = encodeencode("uuencode", True)
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

    data, imports, header, body  = "", "import os", "", ""

    if shebang: data += "#!/usr/bin/env python\n"
    if comment: data += "# Please run this file with Python.\n"

    if len(filenames) == 1 and not os.path.isdir(filenames[0]):
        if not os.path.exists(filenames[0]):
            print "error: %r does not exist" % (filenames[0],)
            sys.exit(1)
        fn, mode, cont = file_data(filenames[0])
        emod, ehead, edecode = encoding.get_dependencies(cont)
        cmod, chead, cdecode = compression.get_dependencies(cont)
        body = ('n=%r\nf=open(n,"w")\nf.write('
                "%s)\nf.close()\nos.chmod(n,%d)" % (fn,
                 cdecode % (edecode % (repr(cont),),), mode))
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

        emod, ehead, edecode = encoding.get_dependencies("", True)
        cmod, chead, cdecode = compression.get_dependencies("", True)

        body = """D=%s
for n in D:
 d=D[n]""" % (compact_repr(files),)
        if needs_dirmach:
            body += """
 if isinstance(d,tuple):f=open(n,"w");f.write(%s);f.close();os.chmod(n,d[0])
 elif not os.path.exists(n):os.mkdir(n)"""
        else:
            body += """
 f=open(n,"w");f.write(%s);f.close();os.chmod(n,d[0)]"""
        body %= (cdecode % (edecode % ("d[1]",),),)

    imports += emod + cmod
    data += (imports + "\n" + ehead + chead + body)

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
                           options.encoding, options.recursive,
                           options.comment, options.shebang)
            f = open(fn, "w")
            f.write(compressed)
            f.close()
        return

    compressed = pypressor(filenames, options.compression,
                           options.encoding, options.recursive,
                           options.comment, options.shebang)
    
    if options.paste:
        url = PastebincomProvider().paste(compressed)
        if url is not None:
            print url
            return
        print "Unable to paste result. Printing instead:"
        
    sys.stdout.write(compressed)

if __name__ == "__main__":
    main()
