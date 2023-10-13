from setuptools import setup, find_packages

with open("requirements.txt") as f:
	install_requires = f.read().strip().split("\n")

# get version from __version__ variable in zk_integration/__init__.py
from zk_integration import __version__ as version

setup(
	name="zk_integration",
	version=version,
	description="Zktecho",
	author="Daniyal AHmad",
	author_email="da100201813@gamil.com",
	packages=find_packages(),
	zip_safe=False,
	include_package_data=True,
	install_requires=install_requires
)
