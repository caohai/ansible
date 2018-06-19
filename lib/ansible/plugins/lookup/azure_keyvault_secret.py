# python 3 headers, required if submitting to Ansible
from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

DOCUMENTATION = """
      lookup: azure_keyvault_secret
        short_description: read secrets from azure key vault.
        description:
            - This lookup returns the contents of a secret kept in azure key vault.
        options:
          _terms:
            description: secret name(s) of secrets to retrieve
            required: True
          vault_url:
            description: url of azure key vault to be retrieved from
            default: 'azure-key-vault'
            required: True
          client_id:
            description: azure client id that has access to the provided azure key vault
          secret:
            description: secret of client_id provided above

        notes:
          - TODO
"""
from ansible.errors import AnsibleError, AnsibleParserError
from ansible.plugins.lookup import LookupBase



class LookupModule(LookupBase):

    def run(self, terms, variables, **kwargs):


        ret = []
        for term in terms:
            ret.append(term)
        return ret