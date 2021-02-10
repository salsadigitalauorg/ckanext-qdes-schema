# Data.Qld migration script

## Setup

__For local development testing:__

Add the gateway IP to `ckan` container:

    ahoy add-gateway-ip ckan qdes-ckan-29.docker.amazee.io
   
This adds `ckan qdes-ckan-29.docker.amazee.io` to the `/etc/hosts` file on the container.

## Run

1. Connect to your `ckan` container, e.g.

        docker-compose exec ckan sh

1. Activate the Python virtual environment:

        . /app/ckan/activate.sh

1. Add OWNER_ORG and HARVEST_API_KEY to environment variable

1. Change to directory to where the script is:

        cd /app/src/ckanext-qdes-schema/ckanext/qdes_schema/qld_harvest

1. Run the script:

        python import.py
