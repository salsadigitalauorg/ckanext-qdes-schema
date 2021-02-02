# QSpatial dataset migration script

The files in this directory provide functionality to 
migrate DES datasets from the QSpatial website (http://qldspatial.information.qld.gov.au/catalogue/) into the DES CKAN Data Catalogue.

## Setup
In it's current form, you need to do perform the following setup steps:

1. Run the `ahoy add-gateway-ip` command - so that the default network gateway IP address 
is added to the `/etc/hosts` file on your local Docker CKAN container

    This will ensure that the `RemoteCKAN` connection can be made to your local CKAN instance
    from within the `ckan` container.

1. Create an API token for the `salsa` user, i.e. with CKAN running locally browse to:
http://qdes-ckan-29.docker.amazee.io/user/salsa/api-tokens - create a new API token then copy
that token to line 27 of the `import_xml.py` file.

## Running the script

First you need to harvest some XML records from QSpatial into your local environment.

1. With the CKAN instance running, `sh` into your `ckan` container, e.g. `docker-compose exec ckan sh`.

1. Activate the Python virtual environment (`. /app/ckan/activate.sh`)

1. Run the `harvest_xml.py` script, e.g.

        cd /app/src/ckanext-qdes-schema/ckanext/qdes-schema/qspatial_harvest
        
        python harvest_xml.py

    This will retrieve 10 XML records and store them as `*.xml` file in the `xml_files`
    directory.

1. Run the `import_xml.py` script to translate & import the XML files into CKAN:

        python import_xml.py

If all goes well - you should now have some new records created in your local CKAN instance.
        
