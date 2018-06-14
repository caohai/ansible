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
from datetime import timedelta

try:
    from msrestazure.tools import parse_resource_id
    from msrestazure.azure_exceptions import CloudError
    from azure.mgmt.monitor.models import (WebhookNotification, EmailNotification, AutoscaleNotification, RecurrentSchedule, MetricTrigger, ScaleAction, AutoscaleSettingResource, AutoscaleProfile, ScaleCapacity, TimeWindow, Recurrence, ScaleRule)
    from ansible.module_utils._text import to_native
except ImportError:
    # This is handled in azure_rm_common
    pass


def timedelta_to_minutes(time):
    if not time:
        return 0
    return time.days * 1440 + time.seconds / 60.0 + time.microseconds / 60000000.0


def get_enum_value(item):
    if 'value' in dir(item):
        return to_native(item.value)
    return to_native(item)


def auto_scale_to_dict(instance):
    if not instance:
        return dict()
    return dict(
        id=to_native(instance.id or ''),
        name=to_native(instance.name),
        location=to_native(instance.location),
        profiles=[profile_to_dict(p) for p in instance.profiles or []],
        notifications=[notification_to_dict(n) for n in instance.notifications or []],
        enabled=instance.enabled,
        target=to_native(instance.target_resource_uri),
        tags=instance.tags
    )


def rule_to_dict(rule):
    if not rule:
        return dict()
    result = dict(metric_name=to_native(rule.metric_trigger.metric_name),
                  metric_resource_uri=to_native(rule.metric_trigger.metric_resource_uri),
                  time_grain=timedelta_to_minutes(rule.metric_trigger.time_grain),
                  statistic=get_enum_value(rule.metric_trigger.statistic),
                  time_window=timedelta_to_minutes(rule.metric_trigger.time_window),
                  time_aggregation=get_enum_value(rule.metric_trigger.time_aggregation),
                  operator=get_enum_value(rule.metric_trigger.operator),
                  threshold=float(rule.metric_trigger.threshold))
    if rule.scale_action and to_native(rule.scale_action.direction) != 'None':
        result['direction'] = get_enum_value(rule.scale_action.direction)
        result['type'] = get_enum_value(rule.scale_action.type)
        result['value'] = to_native(rule.scale_action.value)
        result['cooldown'] = timedelta_to_minutes(rule.scale_action.cooldown)
    return result

def profile_to_dict(profile):
    if not profile:
        return dict()
    result = dict(name=to_native(profile.name),
                  count=to_native(profile.capacity.default),
                  max_count=to_native(profile.capacity.maximum),
                  min_count=to_native(profile.capacity.minimum))
    
    if profile.rules:
        result['rules'] = [rule_to_dict(r) for r in profile.rules]
    if profile.fixed_date:
        result['fixed_date_timezone']=profile.fixed_date.time_zone
        result['fixed_date_start']=profile.fixed_date.start
        result['fixed_date_end']=profile.fixed_date.end
    if profile.recurrence:
        if get_enum_value(profile.recurrence.frequency) != 'None':
            result['recurrence_frequency']=get_enum_value(profile.recurrence.frequency)
        if profile.recurrence.schedule:
            result['recurrence_timezone']=to_native(str(profile.recurrence.schedule.time_zone))
            result['recurrence_days']= [to_native(r) for r in profile.recurrence.schedule.days]
            result['recurrence_hours']=[to_native(r) for r in profile.recurrence.schedule.hours]
            result['recurrence_mins']=[to_native(r) for r in profile.recurrence.schedule.minutes]
    return result


def notification_to_dict(notification):
    if not notification:
        return dict()
    return dict(send_to_subscription_administrator=notification.email.send_to_subscription_administrator if notification.email else False,
                send_to_subscription_co_administrators=notification.email.send_to_subscription_co_administrators if notification.email else False,
                custom_emails=[to_native(e) for e in notification.email.custom_emails or []],
                webhooks=[to_native(w.service_url) for w in notification.webhooks or []])


rule_spec=dict(
    metric_name=dict(type='str', required=True),
    metric_resource_uri=dict(type='str'),
    time_grain=dict(type='float', required=True),
    statistic=dict(type='str', required=True, choices=['Average', 'Min', 'Max', 'Sum'], default='Average'),
    time_window=dict(type='float', required=True),
    time_aggregation=dict(type='str', required=True, choices=['Average', 'Minimum', 'Maximum', 'Total', 'Count'], default='Average'),
    operator=dict(type='str',
                  required=True,
                  choices=['Equals', 'NotEquals', 'GreaterThan', 'GreaterThanOrEqual', 'LessThan', 'LessThanOrEqual'],
                  default='GreaterThan'),
    threshold=dict(type='float', required=True, default=70),
    direction=dict(type='str', choices=['Increase', 'Decrease']),
    type=dict(type='str', choices=['PercentChangeCount', 'ExactCount', 'ChangeCount']),
    value=dict(type='str'),
    cooldown=dict(type='float')
)


profile_spec=dict(
    name=dict(type='str', required=True),
    count=dict(type='str', required=True),
    max_count=dict(type='str'),
    min_count=dict(type='str'),
    rules=dict(type='list', elements='dict', options=rule_spec),
    fixed_date_timezone=dict(type='str'),
    fixed_date_start=dict(type='str'),
    fixed_date_end=dict(type='str'),
    recurrence_frequency=dict(type='str', choices=['None', 'Second', 'Minute', 'Hour', 'Day', 'Week', 'Month', 'Year'], default='None'),
    recurrence_timezone=dict(type='str'),
    recurrence_days=dict(type='list', elements='str'),
    recurrence_hours=dict(type='list', elements='str'),
    recurrence_mins=dict(type='list', elements='str')
)


notification_spec=dict(
    send_to_subscription_administrator=dict(type='bool', aliases=['email_admin'], default=False),
    send_to_subscription_co_administrators=dict(type='bool', aliases=['email_co_admin'], default=False),
    custom_emails=dict(type='list', elements='str'),
    webhooks=dict(type='list', elements='str')
)


class AzureRMAutoScale(AzureRMModuleBase):

    def __init__(self):

        self.module_arg_spec = dict(
            resource_group=dict(type='str', required=True),
            name=dict(type='str', required=True),
            state=dict(type='str', default='present', choices=['present', 'absent']),
            location=dict(type='str'),
            target=dict(type='raw'),
            profiles=dict(type='list', elements='dict', options=profile_spec),
            enabled=dict(type=bool),
            notifications=dict(type='list', elements='dict', options=notification_spec)
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

        self.log('Fetching auto scale settings {0}'.format(self.name))
        results = self.get_auto_scale()
        if  results and self.state == 'absent':
            # delete
            changed = True
            if not self.check_mode:
                self.delete_auto_scale()
        elif self.state == 'present':

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

            def create_rule_instance(params):
                rule = params.copy()
                rule['metric_resource_uri'] = rule.get('metric_resource_uri', self.target)
                rule['time_grain'] = timedelta(minutes=rule.get('time_grain', 0))
                rule['time_window'] = timedelta(minutes=rule.get('time_window', 0))
                rule['cooldown'] = timedelta(minutes=rule.get('cooldown', 0))
                return ScaleRule(metric_trigger=MetricTrigger(**rule), scale_action=ScaleAction(**rule))

            profiles = [AutoscaleProfile(name=p.get('name'),
                                         capacity=ScaleCapacity(minimum=p.get('min_count'),
                                                                maximum=p.get('max_count'),
                                                                default=p.get('count')),
                                         rules=[create_rule_instance(r) for r in p.get('rules', [])],
                                         fixed_date=TimeWindow(time_zone=p.get('fixed_date_timezone'),
                                                               start=p.get('fixed_date_start'),
                                                               end=p.get('fixed_date_end')) if p.get('fixed_date_timezone') else None,
                                         recurrence=Recurrence(frequency=p.get('recurrence_frequency'),
                                                               schedule=RecurrentSchedule(time_zone=p.get('recurrence_timezone'),
                                                                                          days=p.get('recurrence_days'),
                                                                                          hours=p.get('recurrence_hours'),
                                                                                          minutes=p.get('recurrence_mins'))) if p.get('recurrence_frequency') != 'None' else None
                                        ) for p in self.profiles or []]

            notifications = [AutoscaleNotification(email=EmailNotification(**n),
                                                   webhooks=[WebhookNotification(service_uri=w) for w in n.get('webhooks', [])]) for n in self.notifications or []]

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
                profile_result_set = set([str(profile_to_dict(p)) for p in results.profiles or []])
                if profile_result_set != set([str(profile_to_dict(p)) for p in profiles]):
                    changed = True
                notification_result_set = set([str(notification_to_dict(n)) for n in results.notifications or []])
                if notification_result_set != set([str(notification_to_dict(n)) for n in notifications]):
                    changed = True
            if changed:
                # construct the instance will be send to create_or_update api
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
        except Exception as exc:
            self.log('Error: failed to get auto scale settings {0} - {1}'.format(self.name, str(exc)))
            return None

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
