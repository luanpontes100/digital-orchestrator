from requests import get, post, patch, delete
import json, sys, yaml, subprocess
from time import sleep

option = sys.argv[1]
baseurl = "https://api.digitalocean.com/v2"
config_file = 'config.yaml'
with open(config_file, 'r') as file:
    token = yaml.load(file)['token']

def create_kube_cluster():
    url = f'{baseurl}/kubernetes/clusters'
    headers = {'content-type': 'application/json', 'Authorization': f'Bearer {token}'}
    payload = {
                "name": "teste-bv-kubernetes",
                "region": "nyc3",
                "version": "latest",
                "node_pools": [
                    {
                    "size": "s-2vcpu-4gb",
                    "count": 1,
                    "name": "botvendasdo"
                    }
                ]
            }
    r_create = post(url,data=json.dumps(payload),headers=headers)
    print(r_create.json())
    kube_uuid = r_create.json()['kubernetes_cluster']['id']
    with open(config_file, 'r') as file:
        data = yaml.load(file)
    data['kube_uuid'] = kube_uuid
    with open(config_file, 'w') as file:
        file.write(yaml.dump(data, default_flow_style=False))
    install_apps = install_kube_apps(kube_uuid)

    urlstatus = f'{baseurl}/kubernetes/clusters/{kube_uuid}'
    kube_status = None
    while kube_status != 'running':
        print("Waiting the cluster to be created")
        r = get(urlstatus,headers=headers)
        r_json = r.json()
        kube_status = r_json['kubernetes_cluster']['status']['state']
        sleep(20)
     
    activate = subprocess.run(["doctl","kubernetes","cluster","kubeconfig","save", kube_uuid])
    dns = change_dns_record(kube_uuid)
    registry = digital_registry(kube_uuid)

    return r_create.json(), install_apps, activate, dns, registry

def install_kube_apps(kube_uuid):
    url = f'{baseurl}/1-clicks/kubernetes'
    headers = {'content-type': 'application/json', 'Authorization': f'Bearer {token}'}
    payload = {
                "addon_slugs": [
                    "ingress-nginx",
                    "metrics-server"
                ],
                "cluster_uuid": kube_uuid
                }
    response = post(url, headers=headers, data=json.dumps(payload))  
    return response.json()

def get_loadbalancer_ip(kube_uuid):
    url = f'{baseurl}/kubernetes/clusters/{kube_uuid}/destroy_with_associated_resources'
    headers = {'content-type': 'application/json', 'Authorization': f'Bearer {token}'}
    load_uuid = None
    while load_uuid is None:
        r = get(url,headers=headers)
        load_uuid = r.json()['load_balancers'][0]['id'] if r.json()['load_balancers'][0]['id'] else None
        print('Waiting Load Balancer creation')
        sleep(10)
    load_status = None
    while load_status != 'active':
        url = f'{baseurl}/load_balancers/{load_uuid}'
        r = get(url,headers=headers)
        load_status = r.json()['load_balancer']['status']
        print("Waiting IP from Load Balancer")
        
    ip = r.json()['load_balancer']['ip']
    print("ip é: ", ip)

    return ip

def change_dns_record(kube_uuid):
    url = f'{baseurl}/domains/botvendas.com/records?name=teste102.botvendas.com'
    headers = {'content-type': 'application/json', 'Authorization': f'Bearer {token}'}
    record = get(url,headers=headers)
    domain_id = record.json()['domain_records'][0]['id']
    url = f'{baseurl}/domains/botvendas.com/records/{domain_id}'
    ip = get_loadbalancer_ip(kube_uuid)
    payload = {
            "data": f"{ip}",
            "type": "A"
            }
    update = patch(url,data=json.dumps(payload),headers=headers)
    
    return update.json()

def digital_registry(kube_uuid):
    url = f'{baseurl}/kubernetes/registry'
    headers = {'content-type': 'application/json', 'Authorization': f'Bearer {token}'}
    payload = {
        "cluster_uuids": [
            kube_uuid
        ]
    }
    request = post(url,data=json.dumps(payload), headers=headers)
   
    return request.json()

def delete_kube_cluster():
    with open(config_file, 'r') as file:
        data = yaml.load(file)
    kube_uuid = data['kube_uuid']
    deactivate = subprocess.run(["doctl","kubernetes","cluster","kubeconfig","remove", kube_uuid])
    url = f'{baseurl}/kubernetes/clusters/{kube_uuid}/destroy_with_associated_resources/dangerous'
    headers = {'content-type': 'application/json', 'Authorization': f'Bearer {token}'}
    response = delete(url,headers=headers)
    if response.status_code == 204:
        data['kube_uuid'] = None
        with open(config_file, 'w') as file:
            file.write(yaml.dump(data, default_flow_style=False))
    print(response.status_code)
    
    return deactivate


if __name__ == '__main__':
    if option == 'create':
        created = create_kube_cluster()
        print(created)
    elif option == 'delete':
        deleted = delete_kube_cluster()
        print(deleted)