import os.path
import subprocess

from setuptools import setup

with open(os.path.join(os.path.dirname(__file__), 'README.md')) as f:
    readme = f.read()

with open(os.path.join(os.path.dirname(__file__), 'version')) as f:
    version = f.read()

#subprocess.call(['make', '-C', 'src'])
print(readme)

setup(name='WRDice',
      version=version,
      python_requires='>=3.8.10',
      description='Python simulator for war room battles',
      long_description=readme,
      long_description_content_type="text/markdown",
      author='theterminator',
      author_email='warroom@theterminator.e4ward.com',
      url='',
      packages=['wrdice'],
      install_requires=['numpy', 
                        'tqdm',
                        ],
      classifiers=[
          'Development Status :: 1 - Planning',
          'Intended Audience :: Developers',
          'License :: OSI Approved :: GNU Affero General Public License v3 or later (AGPLv3+)',
          'Operating System :: OS Independent',
          'Programming Language :: Python',
          'Programming Language :: C',
          ],
     )
