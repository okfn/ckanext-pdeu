from setuptools import setup, find_packages
import sys, os

version = '0.1'

setup(
	name='ckanext-pdeu',
	version=version,
	description="CKAN extension for publicdata.eu",
	long_description="""\
	""",
	classifiers=[], # Get strings from http://pypi.python.org/pypi?%3Aaction=list_classifiers
	keywords='',
	author='okfn',
	author_email='info@okfn.org',
	url='',
	license='',
	packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
	namespace_packages=['ckanext', 'ckanext.pdeu'],
	include_package_data=True,
	zip_safe=False,
	install_requires=[
		# -*- Extra requirements: -*-
	],
	entry_points=\
	"""
        [ckan.plugins]
	# Add plugins here
	data_publica_harvester=ckanext.pdeu.harvesters:DataPublicaHarvester
	opengov_se_harvester=ckanext.pdeu.harvesters:OpenGovSeHarvester
	""",
)
