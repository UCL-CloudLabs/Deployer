import os
import json
from azure.common.credentials import ServicePrincipalCredentials
from azure.mgmt.resource import ResourceManagementClient
from azure.mgmt.resource.resources.models import DeploymentMode

class Deployer:
    '''
    Deploys a VM on an Azure subscription using a tenant ID and secret stored
    on the machine running this app. The needed env vars can be found on
    Azure's portal:
     * AZURE_TENANT_ID: 'cloudlabs' Azure Active Directory tenant id.
     * AZURE_CLIENT_ID: 'cloudlabs' Azure AD Application Client ID.
     * AZURE_CLIENT_ID: with your Azure AD Application Secret.
     * AZURE_SUBSCRIPTION_ID: UCL RSDG's Azure subscription ID.
    '''
    def __init__(self):
        self.env = self.load_env_vars()
        self.ssh_key = self.load_ssh_key()

    def load_env_vars(self):
        '''
        Load Azure's env vars from local environment.
        '''
        env = {}
        for var in ['AZURE_TENANT_ID', 'AZURE_CLIENT_ID',
                    'AZURE_CLIENT_SECRET', 'AZURE_SUBSCRIPTION_ID']:
            try:
                env[var] = os.environ[var]
            except KeyError:
                print("Environmental variable {} not found. Please set it up "
                      "with the relevant value found in Azure's portal.")
        return env

    def load_ssh_key(self):
        '''
        User's default SSH keys. Needed to be able to configure the machine
        for loging in.
        '''
        with open(os.path.expanduser('~/.ssh/id_rsa.pub'), 'r') as f:
            ssh_key = f.read()
        return ssh_key

    def create_client(self, resource_group):
        '''
        Creates an Azure client using SP credentials.
        '''
        credentials = ServicePrincipalCredentials(
            client_id=self.env['AZURE_CLIENT_ID'],
            secret=self.env['AZURE_CLIENT_SECRET'],
            tenant=self.env['AZURE_TENANT_ID']
        )

        client = ResourceManagementClient(credentials,
                                          self.env['AZURE_SUBSCRIPTION_ID'])

        client.resource_groups.create_or_update(
            resource_group,
            {
                'location':'westus'
            }
        )
        return client

    def set_deployment_properties(self, vm_name):
        '''
        Load automation script template and replace with user input data.
        '''
        with open('deployer/azure/automation_script.json', 'r') as f:
            template = json.load(f)

        parameters = {
            'sshKeyData': self.ssh_key,
            'vmName': vm_name,
            'dnsLabelPrefix': 'aa1a'
        }
        parameters = {k: {'value': v} for k, v in parameters.items()}

        return {
            'mode': DeploymentMode.incremental,
            'template': template,
            'parameters': parameters
        }


    def deploy(self, vm_name):
        '''
        Deploy machine with given parameters on Azure.
        '''
        resource_group = '{}_RG'.format(vm_name)
        client = self.create_client(resource_group)
        deployment_properties = self.set_deployment_properties(vm_name)

        deployment_async_operation = client.deployments.create_or_update(
            resource_group,
            'azure-deployment-sample',
            deployment_properties
        )

        deployment_async_operation.wait()

        return "Deployed!"
