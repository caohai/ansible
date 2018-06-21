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
import requests
import json

TOKEN_ACQUIRED = False

token_params = {
  'api-version':'2018-02-01',
  'resource':'https://vault.azure.net'
  }
token_headers = {
  'Metadata':'true'
  }
token = None
try:
  token_res = requests.get('http://169.254.169.254/metadata/identity/oauth2/token', params = token_params, headers = token_headers)
  token = token_res.json()["access_token"]
  TOKEN_ACQUIRED = True
except requests.exceptions.RequestException as e:
  print('Unable to fetch MSI token.')
  TOKEN_ACQUIRED = False
print(token)

class LookupModule(LookupBase):

    def run(self, terms, variables, **kwargs):


        ret = []
        vault_url = kwargs.pop('vault_url',None)
        if TOKEN_ACQUIRED:
          secret_params = {'api-version':'2016-10-01'}
          secret_headers = {'Authorization':'Bearer ' + token}
          for term in terms[0]:
            try:
              secret_res = requests.get(vault_url + 'secrets/' + term, params = secret_params, headers = secret_headers)
              ret.extend(self._flatten_hash_to_list({term:secret_res.json()["value"]}))
              #ret[term] = secret_res.json()["value"]
            except:
              print('Failed to fetch secret: ' + term + ' via MSI endpoint.')
              ret.extend(self._flatten_hash_to_list({term:''}))
              #ret[term] = None
          print(ret)
          return ret
        else:
          # No MSI, Use Azure key vault client
          # To do
          try:
            from azure.common.credentials import ServicePrincipalCredentials
            from azure.keyvault import KeyVaultClient
          except ImportError:
            raise AnsibleError('The azure_keyvault_secret lookup plugin requires azure.keyvault and akv_vars to be installed.')
          client_id = kwargs.pop('client_id',None)
          key = kwargs.pop('key',None)
          tenant_id = kwargs.pop('tenant_id',None)

          credentials = ServicePrincipalCredentials(
            client_id = client_id,
            secret = key,
            tenant = tenant_id
          )

          client = KeyVaultClient(credentials)

          for term in terms[0]:
            secret = client.get_secret(vault_url,term,'').value
            ret.extend(self._flatten_hash_to_list({term:secret}))

          return ret
