from distutils.core import setup
from distutils.extension import Extension
from Cython.Distutils import build_ext
import numpy as np

ext_modules = [Extension("pycorrmax",
                         ["argmax.pyx"],
                         library_dirs=['./'],
                         libraries=['corrmax'],
                         runtime_library_dirs=['./'])]

setup(
    name = 'pycorrmax',
    cmdclass = {'build_ext': build_ext},
    include_dirs = [np.get_include()],
    ext_modules = ext_modules)

