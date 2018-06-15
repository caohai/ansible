#!/usr/bin/python
#
# Copyright (c) 2017 Yuwei Zhou, <yuwzho@microsoft.com>
#
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type


ANSIBLE_METADATA = {'metadata_version': '1.1',
                    'status': ['preview'],
                    'supported_by': 'community'}


DOCUMENTATION = '''
---
module: azure_rm_autoscale_facts
version_added: "2.7"
short_description: Get Auto Scale Setting facts.
description:
    - Get facts of Auto Scale Setting.

options:
    resource_group:
        description:
            - The name of the resource group.
        required: True
    container_group_name:
        description:
            - The name of the Auto Scale Setting.
    format:
        description:
            - Format of the data returned.
            - If C(raw) is selected information will be returned in raw format from Azure Python SDK.
            - If C(curated) is selected the structure will be identical to input parameters of azure_rm_virtualmachine_scaleset module.
            - In Ansible 2.5 and lower facts are always returned in raw format.
        default: 'raw'
        choices:
            - 'curated'
            - 'raw'

extends_documentation_fragment:
    - azure
    - azure_tags

author:
    - "Yuwei Zhou (@yuwzho)"

'''

EXAMPLES = '''
  - name: Get instance of Auto Scale Setting
    azure_rm_autoscale_facts:
      resource_group: resource_group_name
      name: auto_scale_name

  - name: List instances of Auto Scale Setting
    azure_rm_autoscale_facts:
      resource_group: resource_group_name
'''

RETURN = '''
azure_autoscale:
    description: List of Azure Scale Settings dicts.
    returned: always
    type: list
'''

from ansible.module_utils.azure_rm_common import AzureRMModuleBase

try:
    from msrestazure.azure_exceptions import CloudError
    from msrest.serialization import Model
    from azure_rm_autoscale import auto_scale_to_dict
except ImportError:
    # This is handled in azure_rm_common
    pass


class AzureRMAutoScaleFacts(AzureRMModuleBase):
    def __init__(self):
        # define user inputs into argument
        self.module_arg_spec = dict(
            resource_group=dict(
                type='str',
                required=True
            ),
            name=dict(
                type='str'
            ),
            format=dict(
                type='str',
                choices=['curated', 'raw'],
                default='raw'
            )
        )
        # store the results of the module operation
        self.results = dict()
        self.resource_group = None
        self.format = None
        self.name = None
        self.tags = None
        super(AzureRMAutoScaleFacts, self).__init__(self.module_arg_spec)

    def exec_module(self, **kwargs):
        for key in list(self.module_arg_spec) + ['tags']:
            setattr(self, key, kwargs[key])

        if self.resource_group and self.name:
            self.results['autoscales'] = self.get()
        elif self.resource_group:
            self.results['autoscales'] = self.list_by_resource_group()
        return self.results

    def get(self):
        result = []
        try:
            instance = self.monitor_client.autoscale_settings.get(self.resource_group, self.name)
            result = [self.format_item(instance)]
        except CloudError as e:
            self.log('Could not get facts for autoscale {0} - {1}.'.format(self.name, str(e)))
        return result

    def list_by_resource_group(self):
        results = []
        try:
            response = self.monitor_client.autoscale_settings.list_by_resource_group(self.resource_group)
            results = [self.format_item(item) for item in response if self.has_tags(item.tags, self.tags)]
        except CloudError as e:
            self.log('Could not get facts for autoscale {0} - {1}.'.format(self.name, str(e)))
        return results

    def format_item(self, item):
        if self.format == 'curated':
            return auto_scale_to_dict(item)
        else:
            return self.serialize_obj(item, 'autoscalesettings')


def main():
    AzureRMAutoScaleFacts()


if __name__ == '__main__':
    main()
