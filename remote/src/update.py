import os
import tarfile

TARBALL = "{tarball}"
GUESTDIR = "{guestdir}"

os.chdir(GUESTDIR)

tar = tarfile.open(TARBALL)

tar.extractall()

tar.close()
