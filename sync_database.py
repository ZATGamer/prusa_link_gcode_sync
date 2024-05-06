import sqlite3
import os


def db_setup_connect(db_file):
    if not os.path.exists(db_file):
        db_setup(db_file)

    return sqlite3.connect(db_file)


def db_setup(db):
    print("Creating the Database for the first time.")
    sql_create_state_table = """CREATE TABLE IF NOT EXISTS state (
                                    id integer PRIMARY KEY,
                                    printer_number integer,
                                    printer_ip text,
                                    printer_api_user text,
                                    printer_api_password text,
                                    printer_api_key text,
                                    printer_model text,
                                    job_name text,
                                    progress real,
                                    printer_root text,
                                    clone_root text
                                ); """

    conn = sqlite3.connect(db)
    cursor = conn.cursor()
    cursor.execute(sql_create_state_table)
    conn.commit()
    conn.close()


def get_all_printers(conn):
    # Get all printers out of the database to check
    cur = conn.cursor()
    sql = '''SELECT printer_number,
                    printer_ip,
                    printer_api_user,
                    printer_api_key,
                    printer_api_password,
                    printer_model,
                    printer_root,
                    clone_root FROM state'''
    db_printers = cur.execute(sql)
    db_printers = db_printers.fetchall()
    printers = {}
    for printer in db_printers:
        printers[printer[0]] = {}
        printers[printer[0]]['ip'] = printer[1]
        printers[printer[0]]['user'] = printer[2]
        printers[printer[0]]['key'] = printer[3]
        printers[printer[0]]['password'] = printer[4]
        printers[printer[0]]['model'] = printer[5]
        printers[printer[0]]['root_folder'] = printer[6]
        printers[printer[0]]['clone_root'] = printer[7]
    return printers


def data_setup(conn):
    cur = conn.cursor()
    data1 = (1, "p1", "192.168.1.201", "xxx", "xxx", "mk3s+", "local", "\Production-gcode\\Mk3")
    data2 = (2, "p2", "192.168.1.202", "xxx", "xxx", "mk3s+", "local", "\Production-gcode\\Mk3")
    data3 = (3, "p3", "192.168.1.203", "xxx", "xxx", "mk3s+", "local", "\Production-gcode\\Mk3")
    data4 = (4, "p4", "192.168.1.204", "xxx", "xxx", "mk3s+", "local", "\Production-gcode\\Mk3")
    data5 = (5, "p5", "192.168.1.205", "xxx", "xxx", "mk4", "usb", "\Production-gcode\\Mk4")
    data6 = (6, "p6", "192.168.1.206", "xxx", "xxx", "mk3s+", "local", "\Production-gcode\\Mk3")
    data7 = (7, "p7", "192.168.1.207", "xxx", "xxx", "mk3s+", "local", "\Production-gcode\\Mk3")
    data8 = (8, "p8", "192.168.1.208", "xxx", "xxx", "mk4", "usb", "Production-gcode\\Mk4")
    data9 = (9, "p9", "192.168.1.209", "xxx", "xxx", "mini+", "usb", "oduction-gcode\\Mini")
    data11 = (11, "p11", "192.168.1.211", "xxx", "xxx", "mk4", "usb", "roduction-gcode\\XL")
    data12 = (12, "p12", "192.168.1.212", "xxx", "xxx", "mk4", "usb", "oduction-gcode\\Mk4")

    data_sets = [data1, data2, data3, data4, data5, data6, data7, data8, data9, data11, data12]
    #data_sets = [data6]
    sql_create_state_table = """INSERT INTO state (id, printer_number, printer_ip, printer_api_user, printer_api_password, printer_model, printer_root, clone_root) VALUES(?,?,?,?,?,?,?,?); """
    for data_set in data_sets:
        cur.execute(sql_create_state_table, data_set)
    conn.commit()
