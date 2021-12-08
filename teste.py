import yaml, sys

action = sys.argv[1]

def secureconfig(action, data = None):
    config_file = 'config.yaml'
    if action == 'r':
        with open(config_file, 'r') as file:
            print("lendo arquivo")
            data = yaml.load(file)
        return data
    elif action == 'w':
        with open(config_file, 'w') as file:
            print("escrevendo arquivo")
            file.write(yaml.dump(data, default_flow_style=False))
        return 'Ok'

if __name__ == '__main__':
    if action == 'r':
        print(secureconfig(action))
    elif action == 'w':
        data = secureconfig('r')
        data['redis_uuid'] = 'teste luan'
        print(secureconfig('w', data))