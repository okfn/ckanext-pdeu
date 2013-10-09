import setuptools

version = '0.2'

setuptools.setup(
    name='ckanext-pdeu',
    version=version,
    description="CKAN extension for publicdata.eu",
    long_description="""\
    """,
    # Get strings from http://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[],
    keywords='',
    author='okfn',
    author_email='info@okfn.org',
    url='',
    license='',
    packages=setuptools.find_packages(
        exclude=['ez_setup', 'examples', 'tests']),
    namespace_packages=['ckanext', 'ckanext.pdeu'],
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        # -*- Extra requirements: -*-
    ],
    entry_points="""
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
    opendata_cat_harvester=ckanext.pdeu.harvesters:OpenDataCatHarvester
    ckan_berlin_harvester=ckanext.pdeu.harvesters:BerlinCKANHarvester
    ckan_overheid=ckanext.pdeu.harvesters:OverheidHarvester

    [nose.plugins.0.10]
    pdeu_nose_plugin = ckanext.pdeu.pdeu_nose_plugin:PDEUNosePlugin
    """,
)
