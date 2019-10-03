import os
import pathlib
import setuptools


def readme():
    if os.path.isfile('README.md'):
        try:
            import requests
            r = requests.post(
                url='http://c.docverter.com/convert',
                data={'from': 'markdown', 'to': 'rst'},
                files={'input_files[]': open('README.md', 'r')}
            )
            if r.ok:
                return r.content.decode()
            else:
                return 'ERROR CONVERTING README!'
        except ImportError:
            print('No `requests` module. No readme conversion applied.')
            return '!!NO CONVERSION!!\n\n' + open('README.md', 'r').read()
    else:
        return 'No readme for local builds.'


def version():
    versionPath = pathlib.Path(__file__).parent / 'VERSION'
    with versionPath.open('r') as versionFile:
        return versionFile.read().strip()


def requirementsFile(name):
    reqPath = pathlib.Path(__file__).parent / name
    with reqPath.open('r') as reqFile:
        return reqFile.read().strip().splitlines()


setuptools.setup(
    name='guardiandeck',
    version=version(),
    description='Elgato StreamDeck app for managing Destiny 2 inventory',
    long_description=readme(),
    author='Samuel P. Gillispie II',
    author_email='samuel@spgill.me',
    url='https://github.com/spgill/guardiandeck',
    license='MIT',
    packages=['guardiandeck'],
    include_package_data=True,
    install_requires=requirementsFile('requirements.txt'),
    classifiers=[
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3.7'
    ]
)
