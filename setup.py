"""Package configuration."""

from setuptools import setup, find_packages

from pydfuutil import __version__, __author__

CLASSIFIERS = [
    'Intended Audience :: Developers',
    'Natural Language :: English',
    'Programming Language :: Python',
    'Topic :: Software Development :: Libraries :: Python Modules'
]

KEYWORDS = 'dfu_util, dfu-util, pydfu, libusb'

with open('requirements.txt', 'r') as fp:
    setup_requires = fp.readlines()

with open('requirements-dev.txt', 'r') as fp:
    dev_requires = fp.readlines()

with open('README.md', 'r') as fp:
    long_description = fp.read()

package_data = {'pydfuutil': ['requirements.txt', 'requirements-dev.txt']}

setup(
    name='pydfuutil',
    version=__version__,
    python_requires='>=3.9',

    description='pure python fork of dfu_util library',
    long_description=long_description,
    long_description_content_type="text/markdown",

    author=__author__,
    url='https://github.com/o-murphy/pydfuutil',
    download_url='https://github.com/o-murphy/pydfuutil',

    classifiers=CLASSIFIERS,
    keywords=KEYWORDS,

    packages=find_packages(),
    install_requires=setup_requires,
    py_modules=['pydfuutil'],

    extras_require={
        "dev": dev_requires,
    },

    include_package_data=True,
    package_data=package_data,

    # scripts=['scripts/dfu_cli.bat', 'scripts/dfu_cli.sh'],

    zip_safe=False,
    # Include the MANIFEST.in file in the distribution
    # data_files=[('', ['MANIFEST.in'])]  # Add the MANIFEST.in file to the distribution

    # ext_modules=extensions,
    # cmdclass={'install': CustomInstallCommand},
)
