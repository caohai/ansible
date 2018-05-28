# (c) 2018 Yunge Zhu, <yungez@microsoft.com>
# (c) 2017 Ansible Project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

DOCUMENTATION = """
lookup: azure_service_principal_attribute
author:
  - Yunge Zhu <yungez@microsoft.com>
version_added: "2.6"
requirements:

extends_documentation_fragment:
  - azure
short_description: Look up Azure service principal attributes.
description:
  - Describes attributes of your Azure service principal account. You can specify one of the listed
    attribute choices or omit it to see all attributes.
options:
  attribute:
    description: The attribute for which to get the value(s).
    choices:
      - app-id
      - display-name
      - object-id
"""

EXAMPLES = """
vars:
  has_ec2_classic: "{{ lookup('aws_account_attribute', attribute='has-ec2-classic') }}"
  # true | false

  default_vpc_id: "{{ lookup('aws_account_attribute', attribute='default-vpc') }}"
  # vpc-xxxxxxxx | none

  account_details: "{{ lookup('aws_account_attribute', wantlist='true') }}"
  # {'default-vpc': ['vpc-xxxxxxxx'], 'max-elastic-ips': ['5'], 'max-instances': ['20'],
  #  'supported-platforms': ['VPC', 'EC2'], 'vpc-max-elastic-ips': ['5'], 'vpc-max-security-groups-per-interface': ['5']}

"""

RETURN = """
_raw:
  description:
    Returns the value(s) of the attribute (or all attributes if one is not specified).
"""

from ansible.errors import AnsibleError

try:
    from azure.graphrbac import GraphRbacManagementClient
    from msrestazure import azure_cloud
    from msrestazure.azure_exceptions import CloudError
except ImportError:
    raise AnsibleError(
        "The lookup aws_account_attribute requires azure.graphrbac, msrest")


def _boto3_conn(region, credentials):
    boto_profile = credentials.pop('aws_profile', None)

    try:
        connection = boto3.session.Session(
            profile_name=boto_profile).client('ec2', region, **credentials)
    except (botocore.exceptions.ProfileNotFound, botocore.exceptions.PartialCredentialsError) as e:
        if boto_profile:
            try:
                connection = boto3.session.Session(
                    profile_name=boto_profile).client('ec2', region)
            except (botocore.exceptions.ProfileNotFound, botocore.exceptions.PartialCredentialsError) as e:
                raise AnsibleError("Insufficient credentials found.")
        else:
            raise AnsibleError("Insufficient credentials found.")
    return connection


def _get_credentials(options):
    credentials = {}
    credentials['azure_client_id'] = options.get('azure_client_id', None)
    credentials['azure_secret'] = options.get('azure_secret', None)
    credentials['azure_tenant'] = options.get('azure_tenant', 'common')
    credentials['azure_cloud_environment'] = options.get(
        'azure_cloud_environment', None)

    return credentials


class LookupModule(LookupBase):
    def run(self, terms, variables, **kwargs):

        self.set_options(var_options=variables, direct=kwargs)
        credentials = _get_credentials(self._options)

        cloud_environment = azure_cloud.AZURE_PUBLIC_CLOUD
        if credentials['azure_cloud_environment'] is not None:
            cloud_environment = azure_cloud.get_cloud_from_metadata_endpoint(
                credentials['azure_cloud_environment'])

        azure_credentials = ServicePrincipalCredentials(client_id=credentials['azure_client_id'],
                                                        secret=credentials['azure_secret'],
                                                        tenant=credentials['azure_tenant'],
                                                        cloud_environment=cloud_environment,
                                                        resource=cloud_environment.endpoints.active_directory_graph_resource_id,
                                                        verify=false)

        client = GraphRbacManagementClient(
            azure_credentials, credentials['azure_tenant'], base_url=cloud_environment.endpoints.active_directory_graph_resource_id)

        try:
            response = list(client.list(filter="appId eq '{}'".format(
                credentials['azure_client_id'])))[0].object_id

        except CloudError as ex:
            raise AnsibleError(
                "Failed to get service principal object id: %s" % to_native(ex))

        return response.to_dict()
