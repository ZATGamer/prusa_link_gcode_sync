import requests
from requests.auth import HTTPDigestAuth
import json
import os
from pathlib import Path
import datetime
import threading
import sync_database
import renamer


def get_file_size(file):
    file_size = os.path.getsize(file)
    return file_size


def get_printer_files(session, printer, current_path, files, folders):
    local_folders = []
    url = 'http://{}/api/v1/files/{}'.format(printer['ip'], current_path)
    session.headers.update({'Content-type': 'application/json'})
    req = session.get(url).content
    raw_files = json.loads(req)
    for file in raw_files['children']:
        # print(file)
        if file['type'] == 'PRINT_FILE':
            cp = current_path
            if current_path.startswith('usb'):
                cp = cp[3:]
            elif current_path.startswith('local'):
                cp = cp[5:]
            files.append(cp + '/' + file['display_name'])
        elif file['type'] == 'FOLDER':
            local_folders.append(current_path + '/' + file['display_name'])
            folders.append(current_path + '/' + file['display_name'])
    if folders:
        for folder in local_folders:
            # print(folder)
            get_printer_files(session, printer, folder, files, folders)


def get_os_files(path, files):
    file_types = ['*.gcode', '*.bgcode']
    for file_type in file_types:
        for file in Path(path).rglob(file_type):
            s = str(file.parent)
            s = s.replace(path, '')
            s = s.replace('\\', '/')
            # print("{}/{}".format(s, file.name))
            files.append("{}/{}".format(s, file.name))


def printing_file(session, printer, file):
    url = 'http://{}/api/v1/files/{}{}'.format(printer['ip'], printer['root_folder'], file)
    headers = session.head(url).headers
    if printer['model'] == 'mk4' or printer['model'] == 'mini+':
        if headers['Currently-Printing'] == 'false':
            return False
        if headers['Currently-Printing'] == 'true':
            return True
    elif printer['model'] == 'mk3s+':
        if headers['Currently-Printed'] == 'false':
            return False
        if headers['Currently-Printed'] == 'true':
            return True


def copy_file(session, printer, os_path, file):
    db = sync_database.db_setup_connect(db_file)
    url = 'http://{}/api/v1/files/{}{}'.format(printer['ip'], printer['root_folder'], file)
    local_file_path = os_path + file
    file_size = get_file_size(local_file_path)

    if file_size != 0:
        session.headers.update({'Accept': 'application/json',
                   'Content-Length': str(file_size),
                   'Content-Type': 'text/x.gcode',
                   'Connection': 'keep-alive'
                   })
        # Update the database with current file being uploaded.
        print('{}\n{}\n'.format(file, printer['ip']))
        sql = '''UPDATE state set job_name = '{}' WHERE printer_ip = '{}' '''.format(file, printer['ip'])
        cur = db.cursor()
        cur.execute(sql)
        db.commit()

        print('Copying: {} to Printer: {}'.format(local_file_path, printer['ip']))
        session.get('http://{}/api/printer'.format(printer['ip']))
        try:
            session.put(url, data=open(local_file_path, 'rb'))
        except requests.exceptions.ChunkedEncodingError:
            print("Connection Force Closed, Probably because the printer loaded the file preview on the screen.")
        sql = '''UPDATE state set job_name = '{}' WHERE printer_ip = '{}' '''.format(None, printer['ip'])
        cur = db.cursor()
        cur.execute(sql)
        db.commit()
    else:
        print('Skipping {} as its file size is {}'.format(local_file_path, file_size))


def delete_file(session, printer, file_name):
    if not printing_file(session, printer, file_name):
        delete_url = 'http://{}/api/v1/files/{}{}'.format(printer['ip'], printer['root_folder'], file_name)
        print("DELETING FILE: {}{}".format(printer['root_folder'], file_name))
        delete_file = session.delete(delete_url)
    else:
        print("Printer is currently printing {}{}".format(printer['root_folder'], file_name))


def get_difference(test_units, golden_sample):
    missing = []
    for file in test_units:
        if file not in golden_sample:
            missing.append(file)
    return missing


def get_same(printer_files, os_files):
    same = []
    for file in printer_files:
        if file in os_files:
            same.append(file)
    return same


def get_delete_copy(session, printer):
    printer_files = []
    printer_folders = []
    get_printer_files(session, printer, printer['root_folder'], printer_files, printer_folders)
    os_files = []
    get_os_files(printer['clone_root'], os_files)

    # Compare Printer to OS to find Deletes
    delete = get_difference(printer_files, os_files)
    # Compare OS to Printer to find Copies
    copy = get_difference(os_files, printer_files)

    # Testing what is the same, This is simply for testing at this point.
    same = get_same(printer_files, os_files)

    return delete, copy, printer_folders


def delete_files_from_printer(session, printer, files):
    print("Deleting Files from printer...")
    for file in files:
        delete_file(session, printer, file)


def copy_files_to_printer(session, printer, files):
    print("Copying Files to printers...")
    for file in files:
        file_copy = threading.Thread(target=copy_file, args=(session, printer, printer['clone_root'], file))
        copy_status = threading.Thread(target=testing, args=(printer,))
        file_copy.start()
        # time.sleep(.1)
        copy_status.start()
        file_copy.join()
        copy_status.join()


def create_session(printer):
    print(printer)
    print("Opening Session to {} which is a {} printer".format(printer['ip'], printer['model']))
    if printer['model'] == 'mk4' or \
            printer['model'] == 'mk3s+' or \
            printer['model'] == 'mini+' or \
            printer['model'] == "xl" or \
            printer['model'] == 'mk3.9':
        s = requests.Session()
        s.auth = HTTPDigestAuth(printer['user'], printer['password'])
        s.headers.update({'Accept': 'application/json',
                          'Connection': 'keep-alive'
                          })
        return s


def create_session_silent(printer):
    if printer['model'] == 'mk4' or printer['model'] == 'mk3s+' or printer['model'] == 'mini+':
        s = requests.Session()
        s.auth = HTTPDigestAuth(printer['user'], printer['password'])
        s.headers.update({'Accept': 'application/json',
                          'Connection': 'keep-alive'
                          })
        return s


def cleanup_empty_folders(session, printer, folders):
    # Check and see if folders are empty, starting with the deepest ones
    print("Cleaning Up Empty Folders")
    folders.reverse()
    for folder in folders:
        url = 'http://{}/api/v1/files/{}'.format(printer['ip'], folder)
        raw_response = session.get(url).content
        response = json.loads(raw_response)
        if not response['children']:
            print("DELETING FOLDER {}".format(folder))
            session.delete(url)
        # else:
        #     print("KEEP FOLDER {}".format(folder))


def get_file_transfer_status(printer):
    db = sync_database.db_setup_connect(db_file)
    x = 0
    while(True):
        url = 'http://{}/api/v1/status'.format(printer['ip'])
        s = create_session_silent(printer)
        raw_respon = s.get(url).content
        response = json.loads(raw_respon)
        # print(response)
        if 'transfer' in response.keys():
            sql = '''UPDATE state set progress = '{}' WHERE printer_ip = '{}' '''.format(response['transfer']['progress'], printer['ip'])
            cur = db.cursor()
            cur.execute(sql)
            db.commit()
            x = 6
            # time.sleep(1)
        else:
            # print("Nothing Transferring")
            sql = '''UPDATE state set progress = '{}' WHERE printer_ip = '{}' '''.format(
                None, printer['ip'])
            cur = db.cursor()
            cur.execute(sql)
            db.commit()
            if x < 5:
                #This was the first run of the loop, we will sleep for .25 of a second to see if things get better.
                x += 1
            else:
                break


def main(printer):
    db = sync_database.db_setup_connect(db_file)
    start = datetime.datetime.now()
    s = create_session(printer)
    delete, copy, folders = get_delete_copy(s, printer)
    delete_files_from_printer(s, printer, delete)
    copy_files_to_printer(s, printer, copy)
    cleanup_empty_folders(s, printer, folders)
    end = datetime.datetime.now()
    print("Time to upload: {} for Printer: {}".format((end - start), printer['ip']))


def main_v2(printer):
    start = datetime.datetime.now()
    s = create_session(printer)
    delete, copy, folders = get_delete_copy(s, printer)
    delete_files_from_printer(s, printer, delete)
    copy_files_to_printer(s, printer, copy)
    cleanup_empty_folders(s, printer, folders)
    end = datetime.datetime.now()
    print("Time to upload: {} for Printer: {}".format((end - start), printer['ip']))


def testing(printer):
    get_file_transfer_status(printer)


def get_printers_from_config():
    with open(config_file) as printers_file:
        raw_printers = json.load(printers_file)
    printers = {}
    for printer in raw_printers['printers']:
        printers[printer] = {}
        printers[printer]['ip'] = raw_printers['printers'][printer]['ip']
        printers[printer]['user'] = raw_printers['printers'][printer]['user']
        printers[printer]['key'] = raw_printers['printers'][printer]['api_key']
        printers[printer]['password'] = raw_printers['printers'][printer]['password']
        printers[printer]['model'] = raw_printers['printers'][printer]['type']
        printers[printer]['root_folder'] = raw_printers['printers'][printer]['remote_path']
        printers[printer]['clone_root'] = raw_printers['printers'][printer]['local_sync_folder']
    return printers


def main_threads():
    conn = sync_database.db_setup_connect(db_file)
    # sync_database.data_setup(conn)
    printers = sync_database.get_all_printers(conn)

    threads = []
    for printer in printers:
        t = threading.Thread(target=main, args=[printers[printer]])
        t.start()
        # main(printers[printer], os_path, conn)
        threads.append(t)
        testing(printers[printer])
    sql = '''SELECT printer_number, printer_ip, job_name, progress FROM state'''

    for thread in threads:
        thread.join()


def main_threads_config():
    printers = get_printers_from_config()

    threads = []
    for printer in printers:
        t = threading.Thread(target=main_v2, args=[printers[printer]])
        t.start()
        threads.append(t)

    for thread in threads:
        thread.join()


db_file = './stats.db'
config_file = './printers.json'

if __name__ == '__main__':
    printers = get_printers_from_config()
    renamer.check_files_for_space_config(printers)
    main_threads_config()
