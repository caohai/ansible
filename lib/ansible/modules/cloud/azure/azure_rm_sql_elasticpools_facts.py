#!/usr/bin/python
#
# Copyright (c) 2017 Zim Kalinowski, <zikalino@microsoft.com>
#
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type


ANSIBLE_METADATA = {'metadata_version': '1.1',
                    'status': ['preview'],
                    'supported_by': 'community'}


DOCUMENTATION = '''
---
module: azure_rm_sql_elasticpools
version_added: "2.5"
short_description: Get ElasticPools facts.
description:
    - Get facts of ElasticPools.

options:
    resource_group_name:
        description:
            - The name of the resource group that contains the resource. You can obtain this value from the Azure Resource Manager API or the portal.
        required: True
    server_name:
        description:
            - The name of the server.
        required: True
    elastic_pool_name:
        description:
            - The name of the elastic pool to be retrieved.
        required: True

extends_documentation_fragment:
    - azure
    - azure_tags

author:
    - "Zim Kalinowski (@zikalino)"

'''

EXAMPLES = '''
      - name: Create sample Sql
        azure_rm_sql_elasticpools:
          resource_group_name:
          server_name:
          elastic_pool_name:
          tags: "{{ tags }}"
          location: "{{ location }}"
          edition: "{{ edition }}"
          dtu: "{{ dtu }}"
          database_dtu_max: "{{ database_dtu_max }}"
          database_dtu_min: "{{ database_dtu_min }}"
          storage_mb: "{{ storage_mb }}"
          zone_redundant: "{{ zone_redundant }}"
'''

from ansible.module_utils.azure_rm_common import AzureRMModuleBase

try:
    from msrestazure.azure_exceptions import CloudError
    from msrestazure.azure_operation import AzureOperationPoller
    from azure.mgmt.sql import SqlManagementClient
    from msrest.serialization import Model
except ImportError:
    # This is handled in azure_rm_common
    pass


class AzureRMElasticPoolsFacts(AzureRMModuleBase):
    def __init__(self):
        # define user inputs into argument
        self.module_arg_spec = dict(
            resource_group_name=dict(
                type='str',
                required=True
            ),
            server_name=dict(
                type='str',
                required=True
            ),
            elastic_pool_name=dict(
                type='str',
                required=True
            ),
        )
        # store the results of the module operation
        self.results = dict(
            changed=False,
            ansible_facts=dict(azure_dnsrecordset=[])
        )
        self.resource_group_name = None
        self.server_name = None
        self.elastic_pool_name = None
        super(AzureRMElasticPoolsFacts, self).__init__(self.module_arg_spec)

    def exec_module(self, **kwargs):
        for key in self.module_arg_spec:
            setattr(self, key, kwargs[key])

        if (self.resource_group_name is not None and
                self.server_name is not None and
                self.elastic_pool_name is not None):
            self.results['ansible_facts']['get'] = self.get()
        elif (self.resource_group_name is not None and
              self.server_name is not None):
            self.results['ansible_facts']['list_by_server'] = self.list_by_server()
        return self.results

    def get(self):
        '''
        Gets facts of the specified ElasticPools.

        :return: deserialized ElasticPoolsinstance state dictionary
        '''
        self.log("Checking if the ElasticPools instance {0} is present".format(self.resource_group_name))
        found = False
        try:
            response = self.mgmt_client.elastic_pools.get(self.resource_group_name,
                                                          self.server_name,
                                                          self.elastic_pool_name)
            found = True
            self.log("Response : {0}".format(response))
            self.log("ElasticPools instance : {0} found".format(response.name))
        except CloudError as e:
            self.log('Did not find the ElasticPools instance.')
        if found is True:
            return response.as_dict()

        return False

    def list_by_server(self):
        '''
        Gets facts of the specified ElasticPools.

        :return: deserialized ElasticPoolsinstance state dictionary
        '''
        self.log("Checking if the ElasticPools instance {0} is present".format(self.resource_group_name))
        found = False
        try:
            response = self.mgmt_client.elastic_pools.list_by_server(self.resource_group_name,
                                                                     self.server_name)
            found = True
            self.log("Response : {0}".format(response))
            self.log("ElasticPools instance : {0} found".format(response.name))
        except CloudError as e:
            self.log('Did not find the ElasticPools instance.')
        if found is True:
            return response.as_dict()

        return False


def main():
    AzureRMElasticPoolsFacts()
if __name__ == '__main__':
    main()
