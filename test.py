try:
    from cStringIO import StringIO as BytesIO
except ImportError:
    from io import BytesIO

import pycdlib

iso = pycdlib.PyCdlib()
iso.new(udf='2.60')
foostr = b'foo\n'
iso.add_fp(BytesIO(foostr), len(foostr), '/FOO.;1', udf_path='/foo')
iso.add_directory('/DIR1', udf_path='/dir1')
iso.write('new.iso')
iso.close()
