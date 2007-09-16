from common import *
import conduit.datatypes.File as File
import conduit.Utils as Utils

import os
import tempfile

tmpdir = tempfile.mkdtemp()
ok("Created tempdir %s" % tmpdir, True)

contents = Utils.random_string()
name = Utils.random_string()
tmpFile = File.TempFile(contents)

tmpFile.force_new_filename(name)
ok("Set filename to %s" % name, tmpFile._newFilename == name)

newPath = os.path.join(tmpdir, name)
tmpFile.transfer(tmpdir)
ok("Transferred -> %s" % newPath, os.path.isfile(newPath))

f = File.File(newPath)
ok("File contents = %s" % contents, f.get_contents_as_text() == contents)

finished()
