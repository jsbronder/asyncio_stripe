#!/usr/bin/env python
import os
import setuptools


topdir = os.path.abspath(os.path.join(os.path.dirname(__file__)))

def read(paths):
    with open(os.path.join(topdir, paths), 'r') as fp:
        return fp.read()

setuptools.setup(
        name='asyncio_stripe',
        version='0.1.2',
        description='Asyncio Stripe API bindings',
        license='BSD',
        long_description=(read('README.rst')),
        author='Justin Bronder',
        author_email='jsbronder@cold-front.org',
        url='http://github.com/jsbronder/asyncio_stripe',
        keywords='asyncio stripe api aiostripe',
        packages=['asyncio_stripe'],
        package_data = {
          '': ['*.rst', 'LICENSE'],
        },
        data_files = [
          ('share/asyncio_stripe/', ['README.rst', 'LICENSE']),
        ],
        install_requires=['aiohttp', 'attrs'],
        classifiers=[
            'Development Status :: 4 - Beta',
            'Framework :: AsyncIO',
            'Intended Audience :: Developers',
            'License :: OSI Approved :: BSD License',
            'Operating System :: OS Independent',
            'Programming Language :: Python :: 3 :: Only',
            'Programming Language :: Python :: 3.5',
            'Programming Language :: Python :: 3.6',
            'Topic :: Internet :: WWW/HTTP',
            'Topic :: Software Development :: Libraries :: Python Modules',
        ]
)
