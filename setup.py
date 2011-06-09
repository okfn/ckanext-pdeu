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
    pdeu_customizations=ckanext.pdeu.plugin:PDEUCustomizations
    ckan_pdeu_harvester=ckanext.pdeu.harvesters:PDEUCKANHarvester
	data_publica_harvester=ckanext.pdeu.harvesters:DataPublicaHarvester
	opengov_se_harvester=ckanext.pdeu.harvesters:OpenGovSeHarvester
	data_london_gov_uk_harvester=ckanext.pdeu.harvesters:DataLondonGovUkHarvester
	data_wien_gv_at_harvester=ckanext.pdeu.harvesters:DataWienGvAtHarvester
	opendata_paris_fr_harvester=ckanext.pdeu.harvesters:OpendataParisFrHarvester
	digitaliser_dk_harvester=ckanext.pdeu.harvesters:DigitaliserDkHarvester
	piemonte_harvester=ckanext.pdeu.harvesters:DatiPiemonteItHarvester
	""",
)
