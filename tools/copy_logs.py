import os

def copy_log(log_file):
    with open(log_file) as fp:
        log_data = fp.read()
    lines = log_data.split('\n')
    index = len(lines) - 1
    last_line = lines[index]
    while last_line.strip() == '' and index > 0:
        index -= 1
        last_line = lines[index]
    if 'Generated map:' in last_line and 'output:' in last_line:
        map_dir = last_line.split('output:')[-1].strip()
        if map_dir:
            try:
                with open(os.path.join(map_dir, 'mapmaker.log'), 'w') as fp:
                    fp.write(log_data)
                print('Copied log for', map_dir)
            except FileNotFoundError:
                pass


def copy_logs(log_dir):
    for file in os.listdir(log_dir):
        log_file = os.path.join(log_dir, file)
        if os.path.isfile(log_file) and log_file.endswith('.log'):
            copy_log(log_file)


copy_logs('./logs/mapmaker')
