import os.path
import pickle
import ruamel.yaml
from app.utils.path_utils import PathUtils
from config import CONFIG


if __name__ == "__main__":
    _indexers = []
    _site_path = os.path.join(CONFIG.get_config_path(), "sites")
    cfg_files = PathUtils.get_dir_files(in_path=_site_path, exts=[".yml"])
    for cfg_file in cfg_files:
        with open(cfg_file, mode='r', encoding='utf-8') as f:
            _indexers.append(ruamel.yaml.YAML().load(f))
    with open(os.path.join(CONFIG.get_inner_config_path(), "sites.dat"), 'wb') as f:
        pickle.dump(_indexers, f, pickle.HIGHEST_PROTOCOL)
