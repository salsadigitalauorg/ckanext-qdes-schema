# Data.Qld migration script

## Setup

__For local development testing:__
In it's current form, you need to do perform the following setup steps:

1. Run the `ahoy add-gateway-ip` command - so that the default network gateway IP address 
is added to the `/etc/hosts` file on your local Docker CKAN container

    This will ensure that the `RemoteCKAN` connection can be made to your local CKAN instance
    from within the `ckan` container.

1. With the CKAN instance running, `sh` into your `ckan` container, e.g. `docker-compose exec ckan sh`.

## Running the script

1. SSH into `ckan` container
    #### QA
        lagoon ssh -p qdes-ckan -e develop -s ckan
    #### UAT
        lagoon ssh -p qdes-ckan -e uat -s ckan
    #### Prod
        lagoon ssh -p qdes-ckan -e master -s ckan

1. Activate the Python virtual environment:

        . /app/ckan/activate.sh

1. Setup environment variables for import
    #### Create organisation 'data-qld' for QA or 'department-of-environment-and-science' for UAT/Prod
        ckanapi -r $LAGOON_ROUTE -a ed4cc4fc-2f7d-4678-8ae2-eea4f8a169e1 action organization_create name='data-qld' title='Data QLD'
    #### Set organisation environment variable
        export OWNER_ORG=data-qld
    #### Create API Token for Salsa user via ckanapi
        ckanapi -r $LAGOON_ROUTE -a ed4cc4fc-2f7d-4678-8ae2-eea4f8a169e1 action api_token_create user=salsa name=DATAQLD_HARVEST_API_KEY
    #### Or create API token from web UI 
        http://qdes-ckan-29.docker.amazee.io/user/salsa/api-tokens : Local Dev
        https://ckan-qdes-ckan-develop.au.amazee.io/user/salsa/api-tokens : QA
        https://ckan-qdes-ckan-uat.au.amazee.io/user/salsa/api-tokens : UAT
        https://ckan-qdes-ckan-master.au.amazee.io/user/salsa/api-tokens : Prod
    #### Copy token from response or web UI and set environment variable
        export HARVEST_API_KEY={token}

1. Verify environment variables exist and are correct
    #### URL route used by ckanapi to connect to CKAN instance. Should be the URL route of the environment that the datasets will be imported into
        echo $LAGOON_ROUTE
        http://qdes-ckan-29.docker.amazee.io : Local Dev
        https://ckan-qdes-ckan-develop.au.amazee.io : QA
        https://ckan-qdes-ckan-uat.au.amazee.io : UAT
        https://ckan-qdes-ckan-master.au.amazee.io : Prod

1. Verify data service 'data-qld' is created on environment

1. Change to directory to where the script is:

        cd /app/src/ckanext-qdes-schema/ckanext/qdes_schema/qld_harvest

1. Run the script:

        python import.py

1. Log file is created in the directory `logs` with timestamp as file name

1. Any validation errors are printed to terminal

If all goes well - you should now have some new records created in your CKAN instance.
