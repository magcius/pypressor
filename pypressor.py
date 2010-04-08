#!/usr/bin/env python

import sys
import os.path
import bz2
import zlib

def compact_repr(elem):
    if isinstance(elem, dict):
        return "{" + ','.join("'%s':%s" % (k, compact_repr(v)) for k, v in elem.iteritems()) + "}"
    elif isinstance(elem, tuple):
        return "(" + ','.join(compact_repr(v) for v in elem) + ")"
    return repr(elem)

def pypressor(filenames, compression=bz2, base64=True, linebreak=True, recursive=False, comment=True, shebang=True):
    def compress_string(string):
        final = compression.compress(string)
        if base64:
            final = final.encode("base64")
            if not linebreak:
                final = final.replace("\n", "")
        return final

    def file_data(fn):
        if fn == "-":
            cont = compress_string(sys.stdin.read())
            fn = "stdin"
        else:
            f = open(fn, "r")
            cont = compress_string(f.read())
            mode = os.stat(fn).st_mode
            f.close()
        return fn, mode, cont

    D = {}
    data = ""

    if shebang: data += "#!/usr/bin/env python\n"
    if comment: data += "# Please run this file with Python.\n"

    data += "import os,"+compression.__name__+";"

    if len(filenames) == 1 and not os.path.isdir(filenames[0]):
        if not os.path.exists(filenames[0]):
            print "error: %r does not exist" % (filename,)
            sys.exit(1)
        fn, mode, cont = file_data(filenames[0])
        data += ('n=%r;f=open(n,"w");f.write(%s.decomp'
                 "ress(%r%s));f.close();os.chmod(n,%d)"
                 "" % (fn, compression.__name__, cont,
                       ".decode('base64')" if base64 else "", mode))
    else:
        dir = False
        for filename in filenames:
            if not os.path.exists(filename):
                print "error: %r does not exist" % (filename,)
                sys.exit(1)
            elif os.path.isdir(filename):
                dir = True
                if recursive:
                    context = D
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
                        D[os.path.basename(os.path.abspath(filename))+'/'+os.path.basename(file)] = mode, cont
            else:
                if os.path.basename(filename) != filename:
                    dir = True
                filename, mode, cont = file_data(filename)
                D[filename] = mode, cont

        data += """D=%s
for n in D:
 d=D[n]""" % (compact_repr(D),)
        if dir:
            data += """
 if isinstance(d,tuple):f=open(n,"w");f.write(%s.decompress(d[1]%s));f.close();os.chmod(n,d[0])
 elif not os.path.exists(n):os.mkdir(n)"""
        else:
            data += """
 f=open(n,"w");f.write(%s.decompress(d[1]%s));f.close();os.chmod(n,d[0)]"""
        data = data % (compression.__name__, ".decode('base64')" if base64 else "")
    return data

def main():
    from optparse import OptionParser
    opt = OptionParser(usage="%prog [options] filename1 filename2 ... filenameN")
    opt.add_option("-z", "--zlib", action="store_const", dest="compression",
                   const=zlib, default=bz2, help="Use zlib for compression")
    opt.add_option("-b", "--bz2", action="store_const", dest="compression",
                   const=bz2, help="Use bz2 for compression")
    opt.add_option("--b64", "--no-base64", action="store_false", dest="base64",
                   default=True, help="Don't use base64 when outputting the compressed string")
    opt.add_option("--nl", "--no-newline", action="store_false", dest="linebreak",
                   default=True, help="Strip newlines when outputting the base64 string")
    opt.add_option("-r", "--recursive", action="store_true", dest="recursive",
                   default=False, help="Recursively search folders to compress folders")
    opt.add_option("-I", "--inplace", action="store_true", dest="inplace",
                   default=False, help="Replace files inplace with their compressed versions")
    opt.add_option("--nc", "--no-comment", action="store_false", dest="comment",
                   default=True, help="Don't emit a comment in the compressed version")
    opt.add_option("--ns", "--no-shebang", action="store_false", dest="shebang",
                   default=True, help="Don't emit a shebang in the compressed version")
    options, filenames = opt.parse_args()
    if len(filenames) < 1:
        opt.print_help()
        print
        opt.error("need at least one filename")
    if options.inplace:
        for fn in filenames:
            compressed = pypressor([fn])
            f = open(fn, "w")
            f.write(compressed)
            f.close()
        return

    compressed = pypressor(filenames, options.compression,
                           options.base64, options.linebreak,
                           options.recursive, options.comment,
                           options.shebang)
    print compressed

if __name__ == "__main__":
    main()
