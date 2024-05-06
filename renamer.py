import os
import sync_database


def remove_spaces_folders(path):
    for root, dirs, files in os.walk(path):
        for dir in dirs:
            if ' ' in dir:
                # print("There be a space in: '{}'".format(dir))
                newname = ""
                for letter in dir:
                    if letter != " ":
                        newname = "{}{}".format(newname, letter)
                        # print("Not a space")
                    else:
                        newname = "{}_".format(newname)
                        # print("Space REMVOED")

                print("Renaming {} -> {}".format(os.path.join(root, dir), os.path.join(root, newname)))
                os.renames(os.path.join(root, dir), os.path.join(root, newname))


def remove_space_files(path):
    for root, dirs, files in os.walk(path):
        for file in files:
            if ' ' in file:
                # print("There be a space in: '{}'".format(file))
                newname = ""
                for letter in file:
                    if letter != " ":
                        newname = "{}{}".format(newname, letter)
                        # print("Not a space")
                    else:
                        newname = "{}_".format(newname)
                        # print("Space REMVOED")

                print("Renaming {} -> {}".format(os.path.join(root, file), os.path.join(root, newname)))
                os.renames(os.path.join(root, file), os.path.join(root, newname))


def check_files_for_spaces(db_file):
    conn = sync_database.db_setup_connect(db_file)
    sql = """SELECT clone_root FROM state"""
    cur = conn.cursor()
    clone_folders = cur.execute(sql)
    clone_folders = clone_folders.fetchall()
    unique_folders = []
    for listed_folder in clone_folders:
        if listed_folder[0] not in unique_folders:
            unique_folders.append(listed_folder[0])

    for unique_folder in unique_folders:
        remove_spaces_folders(unique_folder)
        remove_space_files(unique_folder)


def check_files_for_space_config(printers):
    unique_folders = []
    for printer in printers:
        if printers[printer]['clone_root'] not in unique_folders:
            unique_folders.append(printers[printer]['clone_root'])

    for unique_folder in unique_folders:
        remove_spaces_folders(unique_folder)
        remove_space_files(unique_folder)


if __name__ == '__main__':
    # remove_spaces_folders(path)
    db_file = './stats.db'
    check_files_for_spaces(db_file)