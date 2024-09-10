import pickle, os, bz2, shutil
from pathlib import Path

def create_folder(FolderPath):
    try:
        Path(FolderPath).mkdir(parents=True, exist_ok=True)
        os.mkdir(FolderPath)
    except FileExistsError:
        shutil.rmtree(FolderPath)
        os.mkdir(FolderPath)

def load_data(Path, FileName, compress=True):
    data_path = os.path.join(Path, FileName)
    if compress:
        ifile = bz2.BZ2File(data_path, 'rb')
        data = pickle.load(ifile)
        ifile.close()
    else:
        with open(data_path, 'rb') as file:
            data = pickle.load(file)

    return data

def store_data(Path, FileName, data, SubFolder=False, FolderName=None, compress=True):
    if SubFolder:
        folder_path = os.path.join(Path, FolderName)
        try:
            os.mkdir(folder_path)
        except FileExistsError:
            pass

        data_path = os.path.join(folder_path, FileName)
    else:
        data_path = os.path.join(Path, FileName)

    if compress:
        ofile = bz2.BZ2File(data_path, 'wb')
        pickle.dump(data, ofile)
        ofile.close()
    else:
        with open(data_path, 'wb') as file:
            pickle.dump(data, file)

def extend_dict(dict_name, key, value, extend=False, value_type='list'):
    if value_type == 'set':
        if key not in dict_name:
            dict_name[key] = {value}
        elif extend:
            dict_name[key].update(value)
        else:
            dict_name[key].add(value)

    elif value_type == 'list':
        if key not in dict_name:
            dict_name[key] = [value]
        elif extend:
            dict_name[key].extend(value)
        else:
            dict_name[key].append(value)

    else:
        raise ValueError(f'Unsupported value type: {value_type}')

    return dict_name

def safe_call(func, *args, **kwargs):
    try:
        func(*args, **kwargs)
        return True
    except:
        return False
