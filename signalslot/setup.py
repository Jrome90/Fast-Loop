import os.path
import signalslot

from setuptools import setup, find_packages


def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


setup(
    name='signalslot',
    version=signalslot.__version__,
    description='Simple Signal/Slot implementation',
    url='https://github.com/numergy/signalslot',
    long_description=read('README.rst'),
    packages=find_packages(),
    include_package_data=True,
    license='MIT',
    keywords='signal slot',
    install_requires=[
        'six',
        'contexter',
        'weakrefmethod',
    ],
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 3',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
)

