from metaflow.mflog import (    
    BASH_MFLOG,
)

from metaflow.plugins.azure.azure_utils import parse_azure_full_path
from metaflow import R

class NuvolarisEnvironment(object):
    
    def __init__(self):
        pass

    def _get_download_code_package_cmd(self, code_package_url, datastore_type):
        """Return a command that downloads the code package from the datastore. We use various
        cloud storage CLI tools because we don't have access to Metaflow codebase (which we
        are about to download in the command).
        The command should download the package to "job.tar" in the current directory.
        It should work silently if everything goes well.
        """
        if datastore_type == "s3":
            return (
                '%s -m awscli ${METAFLOW_S3_ENDPOINT_URL:+--endpoint-url=\\"${METAFLOW_S3_ENDPOINT_URL}\\"} '
                + "s3 cp %s job.tar >/dev/null"
            ) % (self._python(), code_package_url)
        elif datastore_type == "azure":
            container_name, blob = parse_azure_full_path(code_package_url)
            # remove a trailing slash, if present
            blob_endpoint = "${METAFLOW_AZURE_STORAGE_BLOB_SERVICE_ENDPOINT%/}"
            return "download-azure-blob --blob-endpoint={blob_endpoint} --container={container} --blob={blob} --output-file=job.tar".format(
                blob_endpoint=blob_endpoint,
                blob=blob,
                container=container_name,
            )
        else:
            raise NotImplementedError(
                "We don't know how to generate a download code package cmd for datastore %s"
                % datastore_type
            )

    # Custom implementation to skip the environment setup as we use an ad-hoc runtime
    def get_package_commands(self, code_package_url, datastore_type):
        cmds = [
            BASH_MFLOG,
            "mflog 'Setting up task environment.'",
            "mkdir metaflow",
            "cd metaflow",
            "mkdir .metaflow",  # mute local datastore creation log
            "i=0; while [ $i -le 5 ]; do "
            "mflog 'Downloading code package...'; "
            + self._get_download_code_package_cmd(code_package_url, datastore_type)
            + " && mflog 'Code package downloaded.' && break; "
            "sleep 10; i=$((i+1)); "
            "done",
            "if [ $i -gt 5 ]; then "
            "mflog 'Failed to download code package from %s "
            "after 6 tries. Exiting...' && exit 1; "
            "fi" % code_package_url,
            "TAR_OPTIONS='--warning=no-timestamp' tar xf job.tar",
            "mflog 'Task is starting.'"
        ]
        return cmds

    def _python(self):
            if R.use_r():
                return "python3"
            else:
                return "python"