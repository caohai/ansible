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
module: azure_rm_autoscale
version_added: "2.7"
short_description: Manage Azure image.
description:
    - Create, delete an image from virtual machine, blob uri, managed disk or snapshot.
options:
    resource_group:
        description:
            - Name of resource group.
        required: true
    name:
        description:
            - Name of the image.
        required: true
    location:
        description:
            - Location of the image. Derived from I(resource_group) if not specified.
    state:
        description:
            - Assert the state of the image. Use C(present) to create or update a image and C(absent) to delete an image.
        default: present
        choices:
            - absent
            - present

extends_documentation_fragment:
    - azure
    - azure_tags

author:
    - "Yuwei Zhou (@yuwzho)"

'''

EXAMPLES = '''
- name: Create an image from a virtual machine
  azure_rm_autoscale:
    resource_group: Testing
    name: foobar
    source: testvm001

- name: Create an image from os disk
  azure_rm_autoscale:
    resource_group: Testing
    name: foobar
    source: /subscriptions/XXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXX/resourceGroups/Testing/providers/Microsoft.Compute/disks/disk001
    data_disk_sources:
        - datadisk001
        - datadisk002
    os_type: Linux

- name: Delete an image
  azure_rm_autoscale:
    state: absent
    resource_group: Testing
    name: foobar
    source: testvm001
'''

RETURN = '''
id:
    description: Image resource path.
    type: str
    returned: success
    example: "/subscriptions/XXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXX/resourceGroups/Testing/providers/Microsoft.Compute/images/foobar"
'''  # NOQA

from ansible.module_utils.azure_rm_common import AzureRMModuleBase, format_resource_id

try:
    from msrestazure.tools import parse_resource_id
    from msrestazure.azure_exceptions import CloudError
    from azure.mgmt.monitor.models import (WebhookNotification, EmailNotification, AutoscaleNotification, RecurrentSchedule, MetricTrigger, ScaleAction, AutoscaleSettingResource, AutoscaleProfile, ScaleCapacity, TimeWindow, Recurrence, ScaleRule)
except ImportError:
    # This is handled in azure_rm_common
    pass


def auto_scale_to_dict(instance):
    if not instance:
        return dict()
    return dict(
        id=instance.id,
        name=instance.name,
        location=instance.location,
        profiles=[profile_to_dict(p, instance.target_resource_uri) for p in instance.profiles or []],
        notifications=[notification_to_dict(n) for n in instance.notifications or []],
        enabled=instance.enabled,
        target=instance.target_resource_uri,
        tags=instance.tags
    )


def rule_to_dict(rule, default_uri):
    if not rule:
        return dict()
    return dict(metric_name=rule.metric_trigger.metric_name if rule.metric_trigger else '',
                metric_resource_uri=rule.metric_trigger.metric_resource_uri if rule.metric_trigger else default_uri,
                time_grain=rule.metric_trigger.time_grain if rule.metric_trigger else 'PT1M',
                statistic=rule.metric_trigger.statistic if rule.metric_trigger else 'Average',
                time_window=rule.metric_trigger.time_window if rule.metric_trigger else 'PT10M',
                time_aggregation=rule.metric_trigger.time_aggregation if rule.metric_trigger else 'Average',
                operator=rule.metric_trigger.operator if rule.metric_trigger else 'GreaterThan',
                threshold=rule.metric_trigger.threshold if rule.metric_trigger else 70,
                direction=rule.scale_action.direction if rule.scale_action else 'None',
                type=rule.scale_action.direction if rule.scale_action else 'ChangeCount',
                value=rule.scale_action.direction if rule.scale_action else None,
                cooldown=rule.scale_action.direction if rule.scale_action else 'PT5M')


def profile_to_dict(profile, default_uri):
    if not profile:
        return dict()
    return dict(name=profile.name,
                count=profile.capacity.default,
                max_count=profile.capacity.maximum,
                min_count=profile.capacity.minimum,
                rules=[rule_to_dict(r, default_uri) for r in profile.rules],
                fixed_date_timezone=profile.fixed_date.time_zone if profile.fixed_date else None,
                fixed_date_start=profile.fixed_date.start if profile.fixed_date else None,
                fixed_date_end=profile.fixed_date.end if profile.fixed_date else None,
                recurrence_frequency=str(profile.recurrence.frequency) if profile.recurrence else None,
                recurrence_timezone=str(profile.recurrence.schedule.time_zone) if profile.recurrence and profile.recurrence.schedule else None,
                recurrence_days=str(profile.recurrence.schedule.days) if profile.recurrence and profile.recurrence.schedule else None,
                recurrence_hours=str(profile.recurrence.schedule.hours) if profile.recurrence and profile.recurrence.schedule else None,
                recurrence_mins=str(profile.recurrence.schedule.minutes) if profile.recurrence and profile.recurrence.schedule else None)


def notification_to_dict(notification):
    if not notification:
        return dict()
    return dict(send_to_subscription_administrator=notification.email.send_to_subscription_administrator if notification.email else False,
                send_to_subscription_co_administrators=notification.email.send_to_subscription_co_administrators if notification.email else False,
                custom_emails=notification.email.custom_emails if notification.email else None,
                webhooks=[dict(service_url=w.service_url,
                               properties=w.properties) for w in notification.webhooks] if notification.webhooks else None)


rule_spec=dict(
    metric_name=dict(type='str', required=True),
    metric_resource_uri=dict(type='str'),
    time_grain=dict(type='str', required=True, default='PT1M'),
    statistic=dict(type='str', required=True, choices=['Average', 'Min', 'Max', 'Sum'], default='Average'),
    time_window=dict(type='str', required=True, default='PT10M'),
    time_aggregation=dict(type='str', required=True, choices=['Average', 'Minimum', 'Maximum', 'Total', 'Count'], default='Average'),
    operator=dict(type='str',
                  required=True,
                  choices=['Equals', 'NotEquals', 'GreaterThan', 'GreaterThanOrEqual', 'LessThan', 'LessThanOrEqual'],
                  default='GreaterThan'),
    threshold=dict(type='float', required=True, default=70),
    direction=dict(type='str', choices=['None', 'Increase', 'Decrease'], default='None'),
    type=dict(type='str', choices=['PercentChangeCount', 'ExactCount', 'ChangeCount'], default='ChangeCount'),
    value=dict(type='str'),
    cooldown=dict(type='str', default='PT5M')
)


profile_spec=dict(
    name=dict(type='str', required=True),
    count=dict(type='int', required=True),
    max_count=dict(type='int'),
    min_count=dict(type='int'),
    rules=dict(type='list', default='[]', elements='dict', options=rule_spec),
    fixed_date_timezone=dict(type='str'),
    fixed_date_start=dict(type='str'),
    fixed_date_end=dict(type='str'),
    recurrence_frequency=dict(type='str', choices=['Second', 'Minute', 'Hour', 'Day', 'Week', 'Month', 'Year']),
    recurrence_timezone=dict(type='str'),
    recurrence_days=dict(type='list', elements='int'),
    recurrence_hours=dict(type='list', elements='int'),
    recurrence_mins=dict(type='list', elements='int')
)


webhook_spec=dict(
    service_url=dict(type='str'),
    properties=dict(type='dict')
)


notification_spec=dict(
    send_to_subscription_administrator=dict(type='bool', alias=['enable_admin']),
    send_to_subscription_co_administrators=dict(type='bool', alias=['enable_co_admin'],),
    custom_emails=dict(type='list', elements='str'),
    webhooks=dict(type='list', elements='dict', options=webhook_spec)
)


class AzureRMAutoScale(AzureRMModuleBase):

    def __init__(self):

        self.module_arg_spec = dict(
            resource_group=dict(type='str', required=True),
            name=dict(type='str', required=True),
            state=dict(type='str', default='present', choices=['present', 'absent']),
            location=dict(type='str'),
            target=dict(type='raw'),
            profiles=dict(type='list', elements=dict, options=profile_spec),
            enabled=dict(type=bool),
            notifications=dict(type='list', elements=dict, options=notification_spec)
        )

        self.results = dict(
            changed=False
        )

        required_if = [
            ('state', 'present', ['target', 'profiles'])
        ]

        self.resource_group = None
        self.name = None
        self.state = None
        self.location = None
        self.tags = None
        self.target = None
        self.profiles = None
        self.notifications = None
        self.enabled = None

        super(AzureRMAutoScale, self).__init__(self.module_arg_spec, supports_check_mode=True, required_if=required_if)

    def exec_module(self, **kwargs):

        for key in list(self.module_arg_spec.keys()) + ['tags']:
            setattr(self, key, kwargs[key])

        results = None
        changed = False

        if not self.location:
            # Set default location
            resource_group = self.get_resource_group(self.resource_group)
            self.location = resource_group.location

        resource_id = self.target
        if isinstance(self.target, dict):
            resource_id = format_resource_id(val=self.target.name,
                                             subscription_id=self.target.subscription_id or self.subscription_id,
                                             namespace=self.target.namespace,
                                             types=self.target.types,
                                             resource_group=self.target.resource_group or self.resource_group)
        self.target = resource_id

        resource_name = self.name

        # trigger resource should be the setting's target uri as default
        for profile in self.profiles or []:
            for rule in profile.get('rules', []):
                rule['metric_resource_uri'] = rule.get('metric_resource_uri', self.target)

        self.log('Fetching auto scale settings {0}'.format(self.name))
        results = self.get_auto_scale()
        if  results and self.state == 'absent':
            # delete
            changed = True
            if not self.check_mode:
                self.delete_auto_scale()
        elif self.state == 'present':
            if not results:
                # create new
                changed = True
            else:
                # check changed
                resource_name = results.autoscale_setting_resource_name or self.name
                update_tags, tags = self.update_tags(results.tags)
                if update_tags:
                    changed = True
                    self.tags = tags
                if self.target != results.target_resource_uri:
                    changed = True
                if self.enabled != results.enabled:
                    changed = True
                # profile_result_set = set([profile_to_dict(p, self.target) for p in results.profiles or []])
                # if profile_result_set != set(self.profiles):
                #     changed = True
                # notification_result_set = set([notification_to_dict(n) for n in results.notifications or []])
                # if notification_result_set != set(self.notifications):
                #     changed = True
            if changed:
                # construct the instance will be send to create_or_update api
                profiles = [AutoscaleProfile(name=p.get('name'),
                                             capacity=ScaleCapacity(minimum=p.get('min_count'),
                                                                    maximum=p.get('max_count'),
                                                                    default=p.get('count')),
                                             rules=[ScaleRule(metric_trigger=MetricTrigger(**r),
                                                              scale_action=ScaleAction(**r)) for r in p.get('rules', [])],
                                             fixed_date=TimeWindow(time_zone=p.get('fixed_date_timezone'),
                                                                   start=p.get('fixed_date_start'),
                                                                   end=p.get('fixed_date_end')) if p.get('fixed_date_timezone') else None,
                                             recurrence=Recurrence(frequency=p.get('recurrence_frequency'),
                                                                   schedule=RecurrentSchedule(time_zone=p.get('recurrence_timezone'),
                                                                                              days=p.get('recurrence_days'),
                                                                                              hours=p.get('recurrence_hours'),
                                                                                              minutes=p.get('recurrence_mins'))) if p.get('recurrence_frequency') else None
                                            ) for p in self.profiles or []]

                notifications = [AutoscaleNotification(email=EmailNotification(**n),
                                                       webhooks=[WebhookNotification(**w) for w in n.get('webhooks')]) for n in self.notifications or []]

                results = AutoscaleSettingResource(location=self.location,
                                                   tags=self.tags,
                                                   profiles=profiles,
                                                   notifications=notifications,
                                                   enabled=self.enabled,
                                                   autoscale_setting_resource_name=resource_name,
                                                   target_resource_uri=self.target)
                if not self.check_mode:
                    results = self.create_or_update_auto_scale(results)
                # results should be the dict of the instance
        self.results = auto_scale_to_dict(results)
        self.results['changed'] = changed
        return self.results

    def get_auto_scale(self):
        try:
            return self.monitor_client.autoscale_settings.get(self.resource_group, self.name)
        except CloudError as cloud_err:
            # Return None iff the resource is not found
            if cloud_err.status_code == 404:
                self.log('{0}'.format(str(cloud_err)))
                return None
            self.fail('Error: failed to get auto scale settings {0} - {1}'.format(self.name, str(cloud_err)))
        except Exception as exc:
            self.fail('Error: failed to get auto scale settings {0} - {1}'.format(self.name, str(exc)))

    def create_or_update_auto_scale(self, param):
        try:
            return self.monitor_client.autoscale_settings.create_or_update(self.resource_group, self.name, param)
        except Exception as exc:
            self.fail("Error creating auto scale settings {0} - {1}".format(self.name, str(exc)))

    def delete_auto_scale(self):
        self.log('Deleting auto scale settings {0}'.format(self.name))
        try:
            return self.monitor_client.autoscale_settings.delete(self.resource_group, self.name)
        except Exception as exc:
            self.fail("Error deleting auto scale settings {0} - {1}".format(self.name, str(exc)))


def main():
    AzureRMAutoScale()

if __name__ == '__main__':
    main()
