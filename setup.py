#!/usr/bin/env python

from setuptools import setup

setup(
    name='macula',
    version='2.0.0',
    url='https://github.com/threatstream/macula',
    author='Evan Wright',
    author_email='evan.wright@threatstream.com',
    license='Proprietary (C) 2018 ThreatStream, Inc.',
    packages=[
        'models',
        'features',
        'data'
    ],
    package_data={
        'data': ['*.json', '*.csv', '*.model', '*.gz']
    },
    install_requires=[
        'ipython==3.2.1',
        'matplotlib==1.4.3',
        'Momoko==2.1.0',
        'numpy==1.14.5',
        'pandas==0.23.1',
        'scikit-learn==0.19.1',
        'scipy==1.1.0',
        'six==1.9.0',
        'sklearn==0.0',
        'sklearn-pandas==1.6.0',
        'tldextract==1.7.1',
        'tornado==4.2.1',
        'unicodecsv==0.14.1',
        'dateparser==0.3.0',
        'PyYAML==3.11',
        'jdatetime==1.7.1',
        'python-dateutil==2.7.3',
        'requests==2.8.1',
        'matplotlib==2.1.1',
        'xgboost==0.72.1',
        'eli5==0.8'
    ],
    description='Macula Machine Learning Libraries for Scoring and Classifying IOC\'s',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Console',
        'License :: Other/Proprietary License',
        'Operating System :: POSIX',
        'Programming Language :: Other Scripting Engines',
        'Programming Language :: Python :: 2 :: Only',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
    ]
)
