from setuptools import setup, find_packages


install_requires=['PIL']


with open("README.rst") as f:
    README = f.read()

with open("CHANGES.rst") as f:
    CHANGES = f.read()


setup(name='signpic',
      version='0.1',
      packages=find_packages(),
      description="Signpic inserts in yoru pictures a signature",
      long_description=README + '\n' + CHANGES,
      author="Tarek Ziade",
      author_email="tarek@ziade.org",
      include_package_data=True,
      zip_safe=False,
      classifiers=[
        "Programming Language :: Python",
        "Development Status :: 3 - Alpha"],
      install_requires=install_requires,
      entry_points="""
      [console_scripts]
      signpic = signpic.sign:main
      """)
