# python 3 headers, required if submitting to Ansible
from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

DOCUMENTATION = """
      lookup: azure_keyvault_secret
        short_description: read secret from azure key vault.
        description:
            - This lookup returns the content of a secret kept in azure key vault.
        options:
          _terms:
            description: secret name of the secret to retrieve
            required: True
          vault_url:
            description: url of azure key vault to be retrieved from
            default: 'azure-key-vault'
            required: True
          client_id:
            description: client_id of service principal that has access to the provided azure key vault
          key:
            description: key of service principal provided above
          tenant_id:
            description: tenant_id of service principal provided above

        notes:
          - If this plugin is called on an azure virtual machine and the machine has access to the desired key vault via MSI, then you don't need to provide client_id, key, tenant_id.
          - If this plugin is called on a non-azure virtual machine or it's an azure machine has no access to the desired key vault via MSI, then you have to provide a valid service principal that has access to the key vault. 
"""
from ansible.errors import AnsibleError, AnsibleParserError
from ansible.plugins.lookup import LookupBase
import requests
from msrest.exceptions import AuthenticationError,ClientRequestError
from azure.keyvault.models.key_vault_error import KeyVaultErrorException
import logging

logging.getLogger('msrestazure.azure_active_directory').addHandler(logging.NullHandler())
logging.getLogger('msrest.service_client').addHandler(logging.NullHandler())


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
  print('Unable to fetch MSI token. Will use service principal if provided.')
  TOKEN_ACQUIRED = False
#print(token)

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
              #print(secret_res.text)
              ret.append(secret_res.json()["value"])
              #ret.extend(self._flatten_hash_to_list({term:secret_res.json()["value"]}))
              #ret[term] = secret_res.json()["value"]
            except requests.exceptions.RequestException as e:
              print('Failed to fetch secret: ' + term + ' via MSI endpoint.')
              ret.append('')
              #ret.extend(self._flatten_hash_to_list({term:''}))
              #ret[term] = None
          #print(ret)
          return ret
        else:
          # No MSI, Use Azure key vault client
          # To do
          try:
            from azure.common.credentials import ServicePrincipalCredentials
            from azure.keyvault import KeyVaultClient
          except ImportError:
            raise AnsibleError('The azure_keyvault_secret lookup plugin requires azure.keyvault and azure.common.credentials to be installed.')

          client_id = kwargs.pop('client_id',None)
          key = kwargs.pop('key',None)
          tenant_id = kwargs.pop('tenant_id',None)

          try:
            credentials = ServicePrincipalCredentials(
              client_id = client_id,
              secret = key,
              tenant = tenant_id
            )
            client = KeyVaultClient(credentials)
          except AuthenticationError as e:
            raise AnsibleError('Invalid credentials provided.')

          for term in terms[0]:
            try:
              secret = client.get_secret(vault_url,term,'').value
              # ret.extend(self._flatten_hash_to_list({term:secret}))
              ret.append(secret)
            except ClientRequestError as e:
              raise AnsibleError('Error occurred in request')
            except KeyVaultErrorException as e:
              print('Failed to fetch secret: ' + term)
              ret.append('')
          #print('This is azure key vault client version')
          return ret
