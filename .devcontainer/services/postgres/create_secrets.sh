#!/bin/bash

# create_secrets_for_build.sh
# Purpose: Reads secrets from secrets.json and prepares them for Docker build using --secret flag.

# Exit on any error
set -e

JSON_FILE=${1}

# Get CLI arguments and verify JSON file
case "${JSON_FILE}" in
    -h|--help)
        echo "Usage: $0 [secrets.json]"
        echo "Prepares secrets from secrets.json for use with 'docker build --secret'."
        echo "Ensure jq is installed and secrets.json is present in the current directory."
        echo "Outputs a list of --secret flags to include in your docker build command."
        exit 0
        ;;
    *.json)
        echo "JSON file provided: ${JSON_FILE}"
        if [ ! -f "${JSON_FILE}" ]; then
            echo "Error: File '${JSON_FILE}' not found."
            exit 1
        fi
        echo "Processing secrets from ${JSON_FILE}"
        ;;
    *)
        if [ -n "${JSON_FILE}" ]; then
            echo "Error: Invalid argument '${JSON_FILE}'. Use -h or --help for usage."
            exit 1
        fi
        JSON_FILE="secrets.json"
        ;;
esac

# Check if jq is installed (required for JSON parsing)
if ! command -v jq >/dev/null 2>&1; then
    echo "Error: jq is required to parse JSON. Install it with 'sudo apt-get install jq' or equivalent."
    exit 1
fi

# Check if secrets.json exists
if [ ! -f "${JSON_FILE}" ]; then
    echo "Error: ${JSON_FILE} not found in current directory."
    exit 1
fi

# Temporary directory for secret files
TEMP_DIR=$(mktemp -d)
trap 'rm -rf "${TEMP_DIR}"' EXIT

# Read secrets from JSON and prepare them for docker build
echo "Preparing secrets for docker build..."
SECRET_FLAGS=""
jq -c '.secrets[]' "${JSON_FILE}" | while read -r secret; do
    # Extract name and value
    name=$(echo "$secret" | jq -r '.name')
    value=$(echo "$secret" | jq -r '.value')

    # Create a temporary file for the secret
    secret_file="${TEMP_DIR}/${name}"
    echo -n "$value" > "${secret_file}"

    # Check contents of the secret file
    echo "Secret '${name}' prepared in ${secret_file}, with contents $(cat $secret_file)" || {
        echo "Error: Failed to read secret file ${secret_file}"
        exit 1
    }

    # Add to secret flags for docker build
    SECRET_FLAGS="${SECRET_FLAGS} --secret id=${name},src=${secret_file}"
    docker build ${SECRET_FLAGS} . || {
        echo "Error: Failed to build docker image with secret ${name}"
        exit 1
    }

done

## Output the secret flags to use in docker build command
#echo "Use the following flags with your docker build command:"
#echo "docker build ${SECRET_FLAGS} -t your_image_name ."
#echo "Secrets prepared successfully in ${TEMP_DIR}."
#echo "Note: Secrets are stored temporarily and will be cleaned up on script exit."

